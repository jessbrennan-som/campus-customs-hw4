"""The tools the shop chatbot can use. Each is a plain Python function; PydanticAI shows the model the
function's name, its docstring and the types of its inputs, and the model decides when to call it.

Every tool reads live data (the same products and stock the website shows) and returns a Pydantic model,
so the agent always gets clean, checked facts instead of guessing. Nothing here can see another
customer's account or any password data: the only account tool returns the person asking about themselves.
"""

import re
from typing import Literal

from pydantic_ai import ModelRetry, RunContext

import auth
import lessons
import memory
import pages
import security
import trivia
from catalogue import LOW_STOCK, SIZE_ORDER, find_product, load_products, similar_to
from models import (
    AccountHelp,
    AgentDeps,
    CustomerInfo,
    FeedbackSaved,
    LessonSaved,
    PageInfo,
    Product,
    ProductDetails,
    ProductSummary,
    PurchaseHistory,
    SizeCheck,
    SizeOption,
    StockLine,
    StyleCount,
    TriviaQuestion,
    TriviaResult,
)

MAX_RESULTS = 10
STOP_WORDS = {"the", "and", "for", "with", "any", "you", "have", "got", "that", "this", "something", "looking", "want", "need", "show", "find"}


# ---------- sizes ----------
WORD_SIZES = {"EXTRASMALL": 0, "SMALL": 1, "MEDIUM": 2, "LARGE": 3, "EXTRALARGE": 4, "XXLARGE": 5, "DOUBLEXL": 5}


def size_position(text: str) -> int | None:
    """Where a size sits on the scale XS=0, S=1, M=2, L=3, XL=4, XXL=5. Sizes we don't make fall outside
    0 to 5 (XXS is -1, 3XL is 6). None means we can't tell what size was meant."""
    t = re.sub(r"[\s\-_.]", "", text.upper())
    if t in WORD_SIZES:
        return WORD_SIZES[t]
    if t == "M":
        return 2
    m = re.fullmatch(r"(\d*)(X*)([SL])", t)
    if not m:
        return None
    digits, xs, letter = m.groups()
    if digits and len(xs) != 1:
        return None
    count = int(digits) if digits else len(xs)
    return 3 + count if letter == "L" else 1 - count if count else 1


def size_label(position: int) -> str:
    if 0 <= position < len(SIZE_ORDER):
        return SIZE_ORDER[position]
    return f"{position - 3}XL" if position > 5 else f"{1 - position}XS"


def _stock(product: Product) -> dict[str, int]:
    return {s.size: s.quantity for s in product.sizes}


def _stock_lines(p: Product) -> list[StockLine]:
    """Stock for every size, each labeled in_stock, low_stock (5 or fewer) or sold_out."""
    return [
        StockLine(size=s.size, quantity=s.quantity, status="sold_out" if s.quantity == 0 else "low_stock" if s.quantity <= LOW_STOCK else "in_stock")
        for s in p.sizes
    ]


def _summary(p: Product, reason: str | None = None) -> ProductSummary:
    return ProductSummary(
        product_id=p.product_id,
        name=p.name,
        garment_type=p.garment_type,
        description=p.description,
        price=p.price,
        price_text=f"${p.price:,.2f}",
        colors=p.colors,
        tags=p.search_tags,
        stock_by_size=_stock_lines(p),
        total_stock=p.total_stock,
        reason=reason,
    )


def _get(product_id: str) -> Product:
    product = find_product(product_id.strip())
    if product is None:
        raise ModelRetry(f"There is no product with product_id '{product_id}'. Use search_products to find the right product_id first.")
    return product


# ---------- tools ----------
def search_products(
    ctx: RunContext[AgentDeps],
    query: str = "",
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
    sort_by: Literal["relevance", "price_low", "price_high"] = "relevance",
    limit: int = 6,
    exclude_garment_types: list[str] | None = None,
) -> list[ProductSummary]:
    """Search the shop's products. Use this for any "do you have...", "show me...", "what's under $50" question.
    Each result includes the description, price, colors, tags and the stock for every size, so you can often
    answer without another lookup. Tags (like a college name or a sport) are searched too.

    Args:
        query: words to look for in the name, style, description, colors and tags, e.g. "yale hoodie" or "berkeley".
        garment_type: only this style, e.g. "pullover hoodie", "crewneck sweatshirt", "short-sleeve t-shirt", "quarter-zip pullover".
        color: only products that come in this color, e.g. "navy blue" or "gray".
        max_price: only products at or under this price in dollars.
        size: only products that have this size in stock (XS, S, M, L, XL or XXL).
        sort_by: "relevance" (best match first), "price_low" (cheapest first) or "price_high" (most expensive first).
            Use price_low for "what's your cheapest...", price_high for "what's your most expensive...".
        limit: how many to return (at most 10).
        exclude_garment_types: styles to leave out. Use it right away when a customer says a result was the wrong
            kind of thing (for example ["pullover hoodie"] after they said they didn't want a hoodie).

    What the shop has learned from past customers is applied automatically: if a customer's word has a lesson
    (like "sleeveless"), the wrong styles are left out and the closest styles we carry come first.
    """
    learned = lessons.matching(f"{query} {garment_type or ''}")
    skip_types = [t.lower() for t in (exclude_garment_types or [])] + [t.lower() for l in learned for t in l.not_these]
    preferred = {t.lower() for l in learned for t in l.try_instead}
    kind_wanted = (garment_type or "").lower() if not any(l.customer_term in (garment_type or "").lower() for l in learned) else ""  # "sleeveless" is not a real style name
    ignored = {w for l in learned for w in re.findall(r"[a-z0-9']+", l.customer_term)}  # the catalogue never says these words
    words = [("gray" if w == "grey" else w) for w in re.findall(r"[a-z0-9']+", query.lower()) if len(w) > 2 and w not in STOP_WORDS and w not in ignored]
    wanted_size = size_position(size) if size else None
    scored = []
    for p in load_products():
        if p.total_stock == 0:
            continue
        if kind_wanted and kind_wanted not in p.garment_type.lower():
            continue
        if any(t in p.garment_type.lower() for t in skip_types):
            continue
        if color:
            c = color.lower().replace("grey", "gray")
            if not any(c in x for x in p.colors):
                continue
        if max_price is not None and p.price > max_price:
            continue
        if wanted_size is not None:
            if not 0 <= wanted_size < len(SIZE_ORDER) or _stock(p).get(SIZE_ORDER[wanted_size], 0) == 0:
                continue
        name, kind, tags = p.name.lower(), p.garment_type.lower(), " ".join(p.search_tags)
        rest = " ".join([p.description, *p.colors]).lower()
        hits = [(3 if w in name else 2 if w in kind or w in tags else 1 if w in rest else 0) for w in words]
        if words and (not all(hits)):
            continue
        liked = any(t in p.garment_type.lower() for t in preferred)
        scored.append((sum(hits) + (5 if liked else 0), p))
    if sort_by == "price_low":
        scored.sort(key=lambda t: (t[1].price, t[1].name))
    elif sort_by == "price_high":
        scored.sort(key=lambda t: (-t[1].price, t[1].name))
    else:
        scored.sort(key=lambda t: (-t[0], t[1].name))
    close = {l.customer_term for l in learned}
    return [
        _summary(p, f"Closest we carry to '{', '.join(sorted(close))}' (the shop learned this from customers)" if close and any(t in p.garment_type.lower() for t in preferred) else None)
        for _, p in scored[: max(1, min(limit, MAX_RESULTS))]
    ]


def get_product(ctx: RunContext[AgentDeps], product_id: str) -> ProductDetails:
    """Everything about one product: description, price, colors, tags, and exactly how many are in stock in each size.
    Use this for any question about a specific product's price, description or stock.

    Args:
        product_id: the product's id, as returned by search_products (for example "basic-hoodie-big-yale").
    """
    p = _get(product_id)
    return ProductDetails(
        product_id=p.product_id,
        name=p.name,
        garment_type=p.garment_type,
        description=p.description,
        price=p.price,
        price_text=f"${p.price:,.2f}",
        colors=p.colors,
        tags=p.search_tags,
        stock_by_size=_stock_lines(p),
        low_stock_sizes=[s.size for s in p.sizes if 0 < s.quantity <= LOW_STOCK],
        sold_out_sizes=[s.size for s in p.sizes if s.quantity == 0],
        total_stock=p.total_stock,
    )


def check_size(ctx: RunContext[AgentDeps], product_id: str, size: str) -> SizeCheck:
    """Check whether a product is available in a size. If that size is sold out or isn't one we make (like 3XL
    or XXS), this also finds the nearest size up and the nearest size down that ARE in stock, so you can offer both.

    Args:
        product_id: the product's id, as returned by search_products.
        size: the size the customer asked about, in any form: "M", "medium", "xl", "2XL", "3XL", "extra small".
    """
    p = _get(product_id)
    stock = _stock(p)
    pos = size_position(size)
    if pos is None:
        return SizeCheck(
            product_id=p.product_id, product_name=p.name, requested_size=size.strip(), status="unrecognized_size", quantity=0,
            message=f"I can't tell which size '{size}' means. Our sizes are {', '.join(SIZE_ORDER)}. Ask the customer which one they want.",
        )
    label = size_label(pos)
    offered = 0 <= pos < len(SIZE_ORDER)
    quantity = stock.get(label, 0) if offered else 0

    if quantity > LOW_STOCK:
        return SizeCheck(product_id=p.product_id, product_name=p.name, requested_size=label, status="in_stock", quantity=quantity, message=f"Yes, size {label} is in stock ({quantity} available).")
    if quantity > 0:
        return SizeCheck(
            product_id=p.product_id, product_name=p.name, requested_size=label, status="low_stock", quantity=quantity,
            message=f"Size {label} is in stock but running low: only {quantity} left.",
        )

    # not available: find the nearest size up and the nearest size down that are in stock
    up = next((SizeOption(size=s, quantity=stock[s]) for i, s in enumerate(SIZE_ORDER) if i > pos and stock.get(s, 0) > 0), None)
    down = next((SizeOption(size=s, quantity=stock[s]) for i, s in reversed(list(enumerate(SIZE_ORDER))) if i < pos and stock.get(s, 0) > 0), None)
    why = f"Size {label} is sold out." if offered else f"We don't make size {label}."
    parts = [why]
    parts.append(f"The next size up in stock is {up.size} ({up.quantity} left)." if up else "There is no larger size in stock.")
    parts.append(f"The next size down in stock is {down.size} ({down.quantity} left)." if down else "There is no smaller size in stock.")
    if not up and not down:
        parts = [f"{p.name} is sold out in every size right now."]
    return SizeCheck(
        product_id=p.product_id, product_name=p.name, requested_size=label, status="sold_out" if offered else "not_made",
        quantity=0, next_size_up=up, next_size_down=down, message=" ".join(parts),
    )


def suggest_similar(ctx: RunContext[AgentDeps], product_id: str, size: str | None = None) -> list[ProductSummary]:
    """Products that match another product's style, color or size: the same thing the website's "If you like
    this, consider..." section shows. Use it when a customer likes something and wants more like it.

    Args:
        product_id: the product the customer likes.
        size: the customer's size, if known, to favor products that have it in stock.
    """
    p = _get(product_id)
    wanted = size_position(size) if size else None
    label = size_label(wanted) if wanted is not None and 0 <= wanted < len(SIZE_ORDER) else None
    return [_summary(s, s.reason) for s in similar_to(p, label, limit=4)]


def list_styles(ctx: RunContext[AgentDeps]) -> list[StyleCount]:
    """The kinds of clothing the shop sells (pullover hoodie, crewneck sweatshirt, ...) and how many products each has."""
    counts: dict[str, int] = {}
    for p in load_products():
        counts[p.garment_type] = counts.get(p.garment_type, 0) + 1
    return [StyleCount(garment_type=g, products=n) for g, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def about_me(ctx: RunContext[AgentDeps]) -> CustomerInfo:
    """Who you are talking to: whether they are logged in, and if so their own first name, last name and email.
    This is only ever the person chatting right now, never anyone else. A guest (not logged in) has none of these."""
    u = ctx.deps.user
    if u is None:
        return CustomerInfo(logged_in=False)
    return CustomerInfo(logged_in=True, first_name=u.first_name, last_name=u.last_name, email=u.email)


def my_purchases(ctx: RunContext[AgentDeps]) -> PurchaseHistory:
    """What this logged-in customer has bought before (product, size, colors, date), newest first. Use it ONLY to make
    good recommendations (the styles, colors and sizes they like) and to follow up on a recent purchase. It has no
    payment details. A guest has no purchase history."""
    u = ctx.deps.user
    if u is None:
        return PurchaseHistory(logged_in=False, purchases=[], note="This customer isn't logged in, so there is no purchase history.")
    bought = memory.purchases(u.id)
    note = "These are this customer's own purchases." if bought else "This customer has no purchases on record yet."
    return PurchaseHistory(logged_in=True, purchases=bought, note=note)


def record_feedback(
    ctx: RunContext[AgentDeps],
    product_id: str,
    comment: str,
    rating: int | None = None,
    fit: Literal["runs_small", "true_to_size", "runs_large"] | None = None,
) -> FeedbackSaved:
    """Save what the customer said about a product they bought, so the shop's admins can read it later. Use it
    after you asked how a past purchase worked out and the customer answered, or when they volunteer an opinion
    about something they bought. Only works for products in this customer's own purchases.

    Args:
        product_id: the product they're talking about (from my_purchases).
        comment: what they said, in a short sentence or two, in their own words as closely as you can.
        rating: 1 (hated it) to 5 (loved it), only if they clearly gave or implied one. Don't guess.
        fit: "runs_small", "true_to_size" or "runs_large", only if they said how it fits.
    """
    u = ctx.deps.user
    if u is None:
        return FeedbackSaved(saved=False, message="The customer isn't logged in, so feedback can't be saved.")
    return memory.save_feedback(u.id, product_id.strip(), comment, rating, fit)


def about_this_page(ctx: RunContext[AgentDeps]) -> PageInfo:
    """What page the customer is looking at right now, with live database facts about it: on a product's page, that
    product's description, price and stock in every size, and whether the size they've chosen is available; on any
    page, the product cards you've put on it. Use it whenever the customer says "this", "it", "this one", "what I'm
    looking at" or asks about the page."""
    page = ctx.deps.page
    if page is None:
        return PageInfo(kind="other", description="I can't tell which page the customer is on.")
    product = check = None
    if page.product_id:
        product = get_product(ctx, page.product_id)
        if page.selected_size:
            check = check_size(ctx, page.product_id, page.selected_size)
    shown = [_summary(p) for p in (find_product(i) for i in page.shown_product_ids) if p is not None]
    return PageInfo(kind=page.kind, description=pages.DESCRIPTIONS[page.kind], product=product, selected_size_check=check, cards_on_page=shown)


ACCOUNT_TOPICS = Literal["create_account", "log_in", "forgot_password", "change_password", "log_out", "password_rules", "gift_certificates"]


def account_help(ctx: RunContext[AgentDeps], topic: ACCOUNT_TOPICS) -> AccountHelp:
    """Step-by-step help for account questions: creating an account, logging in or out, a forgotten password,
    changing a password, or what makes a good password. You cannot do these for the customer or see their password;
    this tells you what to point them to.

    Args:
        topic: which account question it is.
    """
    help_by_topic = {
        "create_account": AccountHelp(
            topic=topic, page="/create-account",
            steps=["Open Create Account in the menu.", "Enter first name, last name, email and a password, then the password again to confirm.", "The password has to follow the rules shown as a checklist; you're logged in right after."],
        ),
        "log_in": AccountHelp(topic=topic, page="/login", steps=["Open Log In in the menu.", "Enter your email and password.", "If it keeps failing, use Forgot your password? on that page."]),
        "forgot_password": AccountHelp(
            topic=topic, page="/forgot-password",
            steps=["On the Log In page, choose Forgot your password?", "Enter the email on your account.", "We email a reset link to that address. It works once and expires in 30 minutes.", "Open it and choose a new password."],
        ),
        "change_password": AccountHelp(
            topic=topic, page="/account",
            steps=["Log in, then choose My Account in the menu.", "Enter your current password, then the new one twice.", "Other devices are logged out, and we email you to confirm the change."],
        ),
        "log_out": AccountHelp(topic=topic, page=None, steps=["Choose Log Out in the menu at the top of any page."]),
        "gift_certificates": AccountHelp(
            topic=topic, page="/gift-certificates",
            steps=["Open Gift Certificates in the menu.", "A parent or loved one picks an amount, enters the student's name and email, and adds a note.", "The student gets a code by email. In the cart, they enter the code and choose Pay with gift certificate (they need to be logged in).", "Everything paid for with a gift certificate is 10% off. This is a class project, so no real payment is taken."],
        ),
        "password_rules": AccountHelp(topic=topic, page="/create-account", steps=[f"Passwords need: {rule}." for rule in security.RULES.values()]),
    }
    return help_by_topic[topic]


def start_trivia(ctx: RunContext[AgentDeps]) -> TriviaQuestion:
    """Start a Yale trivia round, or get the next question in the round already going. Only call this after the
    customer says yes to playing. Read the question and every option out EXACTLY as returned, one per line like
    "A. ...", and never make up a question or an answer."""
    return trivia.start(ctx.deps.visitor_key)


def answer_trivia(ctx: RunContext[AgentDeps], answer: str) -> TriviaResult:
    """Check the customer's answer to the trivia question that is waiting. Pass what they typed ("B", "c", or the
    answer's words). The shop decides whether it's right; you only report the result kindly and share the fun fact.

    Args:
        answer: the customer's answer, as they typed it.
    """
    return trivia.answer(ctx.deps.visitor_key, answer)


def learn_from_mistake(
    ctx: RunContext[AgentDeps],
    customer_term: str,
    wrong_garment_types: list[str],
    closest_garment_types: list[str],
    note: str = "",
) -> LessonSaved:
    """Remember a mistake so the shop does better next time. Use it when a customer tells you a result was the wrong
    kind of thing (for example they asked for a sleeveless shirt and you showed a hoodie). Never use it just because we don't carry something,
    and only for styles that are on the customer's page. First fix their search right away (search again with
    exclude_garment_types), then call this once. Use only real garment types from list_styles.

    Args:
        customer_term: the one distinctive word the customer used, like "sleeveless" (not "sleeveless top"; letters only).
        wrong_garment_types: the styles that were wrong for it, like ["pullover hoodie"].
        closest_garment_types: the closest styles we really carry, like ["short-sleeve t-shirt"]. May be empty.
        note: one short sentence about the difference (what the customer meant).
    """
    # a guest counts by network address, not by chat session, because anyone can invent a new session
    reporter = f"user:{ctx.deps.user.id}" if ctx.deps.user else f"ip:{ctx.deps.visitor_key.rsplit(':', 1)[0]}"
    if auth.throttle(f"lesson:{reporter}", 5):
        return LessonSaved(saved=False, message="Thanks, I've already saved several lessons from you. I'll use what I have.")
    # Only a mistake the customer could really have seen: the wrong styles must be among the products on their page.
    on_page = {p.garment_type.lower() for p in (find_product(i) for i in (ctx.deps.page.shown_product_ids if ctx.deps.page else [])) if p}
    unseen = [t for t in wrong_garment_types if t.strip().lower() not in on_page]
    if unseen:
        return LessonSaved(saved=False, message="Nothing was saved: those styles aren't among the products on the customer's page, so they can't have been the mistake. Only record a mistake after the customer says a result they were shown was wrong.")
    return lessons.save(reporter, customer_term, wrong_garment_types, closest_garment_types, note)


ALL_TOOLS = [search_products, get_product, check_size, suggest_similar, list_styles, about_me, my_purchases, record_feedback, about_this_page, account_help, start_trivia, answer_trivia, learn_from_mistake]
