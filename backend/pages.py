"""Which page is the customer looking at? The website tells the API with every chat message (a PageState), and
this file turns that claim into a PageContext the chatbot can rely on.

The browser is not trusted: the path must match one of the website's real pages, a product id must exist in the
database, a size must be one of ours, and card ids must be real products. Anything that doesn't check out is
dropped, so the chatbot never works from invented page details.
"""

import re

import catalogue
from models import PageContext, PageState

PAGES = {
    "/": "home",
    "/products": "products",
    "/about": "about",
    "/gift-certificates": "gift_certificates",
    "/login": "login",
    "/create-account": "create_account",
    "/account": "account",
    "/forgot-password": "forgot_password",
    "/reset-password": "reset_password",
}
PRODUCT_PATH = re.compile(r"^/products/([a-z0-9][a-z0-9-]{0,100})$")


def build_context(state: PageState | None) -> PageContext | None:
    """The checked version of what the browser says about the page, or None if nothing usable was sent."""
    if state is None:
        return None
    path = state.path.split("?")[0].split("#")[0].rstrip("/") or "/"
    known = {p.product_id for p in catalogue.load_products()}

    product_id = None
    if (m := PRODUCT_PATH.match(path)) and m.group(1) in known:
        product_id = m.group(1)
    kind = "product" if product_id else PAGES.get(path, "other")

    size = state.selected_size.strip().upper() if state.selected_size else None
    if size not in catalogue.SIZE_ORDER:
        size = None
    return PageContext(
        kind=kind,
        path=path if kind != "other" else "(another page)",
        product_id=product_id,
        selected_size=size if product_id else None,
        shown_product_ids=[i for i in dict.fromkeys(state.shown_product_ids) if i in known],
    )


DESCRIPTIONS = {
    "home": "the home page: the banner, a few fan favorites, and the Lux et Veritas banner",
    "products": "the Products page, which lists every product with search, style filter and sorting",
    "product": "a product's own page, showing the large photo, price, description, colors, a size picker with how many are in stock in each size, an Add to cart button, and similar products",
    "about": "the About Us page, which tells the story of Campus Customs",
    "gift_certificates": "the Gift Certificates page, where family and friends can buy a digital gift certificate for a student; everything bought with a gift certificate is 10% off",
    "login": "the Log In page",
    "create_account": "the Create Account page",
    "account": "the My Account page, where a logged-in customer can change their password",
    "forgot_password": "the Forgot password page",
    "reset_password": "the page for choosing a new password after a reset email",
    "other": "a page of the website",
}
