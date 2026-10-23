"""Reads the products and their stock from the database. Shared by the shop routes and the chatbot's tools,
so the website and the chatbot always see exactly the same products, prices and stock."""

import json
import re
import sqlite3
from pathlib import Path

from config import DB_PATH, IMAGE_DIR, WHITE_DIR
from models import Product, SimilarProduct, SizeStock

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
LOW_STOCK = 5  # "only a few left" at or below this many


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def image_url(filename: str) -> str:
    """The web address of a photo. The number on the end changes whenever the photo file changes,
    so browsers never keep showing an old cached version of it."""
    for folder in (WHITE_DIR, IMAGE_DIR):
        path = folder / filename
        if path.is_file():
            return f"/images/{filename}?v={int(path.stat().st_mtime)}"
    return f"/images/{filename}"


def load_products() -> list[Product]:
    """Every product with its stock by size, in name order."""
    conn = _connect()
    try:
        stock: dict[str, dict[str, int]] = {}
        for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]
        products = []
        for r in conn.execute("SELECT * FROM catalogue ORDER BY name"):
            by_size = stock.get(r["product_id"], {})
            sizes = [SizeStock(size=s, quantity=by_size[s]) for s in SIZE_ORDER if s in by_size]
            products.append(
                Product(
                    product_id=r["product_id"],
                    name=r["name"],
                    garment_type=r["garment_type"],
                    description=r["description"],
                    colors=json.loads(r["colors"]),
                    search_tags=json.loads(r["search_tags"]),
                    price=r["price"],
                    image_url=image_url(Path(r["image_file_path"]).name),
                    sizes=sizes,
                    total_stock=sum(s.quantity for s in sizes),
                )
            )
        return products
    finally:
        conn.close()


def find_product(product_id: str) -> Product | None:
    return next((p for p in load_products() if p.product_id == product_id), None)


def _family(garment_type: str) -> str:
    """Rough style family, so a pullover hoodie and a full-zip hooded sweatshirt count as related."""
    g = garment_type.lower()
    if "hood" in g:
        return "hoodie"
    if "t-shirt" in g or "performance shirt" in g:
        return "tee"
    if "quarter-zip" in g:
        return "quarter-zip"
    if "jacket" in g or "fleece" in g:
        return "jacket"
    if "crew" in g or "mockneck" in g:
        return "crewneck"
    return g


def similar_to(me: Product, size: str | None = None, limit: int = 3) -> list[SimilarProduct]:
    """Other products that match this one's style, color or size, best match first."""
    everyone = load_products()

    # tags that nearly everything has (like "yale") say nothing about style, so they don't count
    tag_counts: dict[str, int] = {}
    for p in everyone:
        for t in set(p.search_tags):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    useful = {t for t, n in tag_counts.items() if n <= len(everyone) * 0.25}
    my_tags = set(me.search_tags) & useful
    my_sizes_in_stock = {s.size for s in me.sizes if s.quantity > 0}

    scored: list[tuple[float, Product, list[str]]] = []
    for p in everyone:
        if p.product_id == me.product_id or p.total_stock == 0:
            continue
        score, reasons = 0.0, []

        if p.garment_type == me.garment_type:
            score += 4
            reasons.append(f"Same style: {p.garment_type}")
        elif _family(p.garment_type) == _family(me.garment_type):
            score += 2
            reasons.append("A similar style")

        shared_colors = [c for c in p.colors if c in me.colors]
        if shared_colors:
            score += 3 + min(len(shared_colors) - 1, 2)
            reasons.append(f"Also {shared_colors[0]}")

        shared_tags = my_tags & set(p.search_tags)
        if shared_tags:
            score += min(len(shared_tags), 4) * 0.75

        in_stock = {s.size for s in p.sizes if s.quantity > 0}
        if size and size in in_stock:
            score += 2
            reasons.append(f"Your size ({size}) is in stock")
        elif not size and len(in_stock & my_sizes_in_stock) >= 4:
            score += 1
            reasons.append("Available in the sizes you're looking at")

        scored.append((score, p, reasons))

    scored.sort(key=lambda t: (-t[0], t[1].name))
    return [SimilarProduct(**p.model_dump(), reason=" · ".join(reasons) or "Fans of this also like it") for _, p, reasons in scored[:limit]]


# ---------- browsing: categories and "shop for" groups ----------
# What kind of thing is it? The first category whose test matches wins, so order matters
# (a "short-sleeve crew-neck t-shirt" is a T-shirt, not a crewneck).
CATEGORIES: list[tuple[str, str, "re.Pattern[str]"]] = [
    ("hoodies", "Hoodies", re.compile(r"hood")),
    ("t-shirts", "T-shirts", re.compile(r"t-shirt")),
    ("long-sleeve", "Long-sleeve & performance", re.compile(r"performance")),
    ("jackets", "Jackets & fleece", re.compile(r"jacket|fleece")),
    ("quarter-zips", "Quarter-zips", re.compile(r"quarter-zip")),
    ("sweatshirts", "Crewnecks & sweatshirts", re.compile(r"crew|mockneck|sweatshirt")),
]

# Who or what is it for? Each option matches on the product's name. `skip` rules out look-alikes.
GROUPS: list[tuple[str, list[tuple[str, str, str, str | None]]]] = [
    ("Residential colleges", [
        ("benjamin-franklin", "Benjamin Franklin", r"benjamin franklin", None),
        ("berkeley", "Berkeley", r"\bberkeley\b", None),
        ("branford", "Branford", r"\bbranford\b", None),
        ("davenport", "Davenport", r"\bdavenport\b", None),
        ("grace-hopper", "Grace Hopper", r"grace hopper", None),
        ("jonathan-edwards", "Jonathan Edwards", r"jonathan edwards", None),
        ("morse", "Morse", r"\bmorse\b", None),
        ("pierson", "Pierson", r"\bpierson\b", None),
        ("saybrook", "Saybrook", r"\bsaybrook\b", None),
        ("timothy-dwight", "Timothy Dwight", r"timothy dwight", None),
        ("trumbull", "Trumbull", r"\btrumbull\b", None),
    ]),
    ("Schools", [
        ("architecture", "Architecture", r"school of architecture", None),
        ("art", "Art", r"school of art\b", None),
        ("divinity", "Divinity", r"divinity school", None),
        ("engineering", "Engineering", r"school of engineering", None),
        ("forestry", "Forestry & Environment", r"forest school", None),
        ("law", "Law", r"law school", None),
        ("management", "Management", r"school of management", None),
        ("medicine", "Medicine", r"school of medicine", None),
        ("music", "Music", r"school of music", None),
        ("nursing", "Nursing", r"school of nursing", None),
        ("public-health", "Public Health", r"school of public health", None),
    ]),
    ("Sports", [
        ("baseball", "Baseball", r"baseball", None),
        ("basketball", "Basketball", r"basketball", None),
        ("diving", "Diving", r"diving", None),
        ("fencing", "Fencing", r"fencing", None),
        ("field-hockey", "Field hockey", r"field hockey", None),
        ("football", "Football", r"football", None),
        ("golf", "Golf", r"\bgolf\b", None),
        ("hockey", "Ice hockey", r"hockey", r"field hockey"),
        ("lacrosse", "Lacrosse", r"lacrosse", None),
        ("rowing", "Rowing (crew)", r"^crew left chest", None),
        ("sailing", "Sailing", r"sailing", None),
        ("soccer", "Soccer", r"soccer", None),
        ("squash", "Squash", r"squash", None),
        ("swimming", "Swimming", r"swimming", None),
        ("tennis", "Tennis", r"tennis", None),
        ("track-field", "Track & field", r"track", None),
        ("volleyball", "Volleyball", r"volleyball", None),
    ]),
    ("Family & gifts", [
        ("mom", "Mom", r"\bmom\b", None),
        ("dad", "Dad", r"\bdad\b", None),
        ("grandma", "Grandma", r"grandma", None),
        ("grandpa", "Grandpa", r"grandpa", None),
        ("aunt", "Aunt", r"\baunt\b", None),
        ("uncle", "Uncle", r"\buncle\b", None),
        ("brother", "Brother", r"\bbrother\b", r"brooks brothers"),
        ("cousin", "Cousin", r"\bcousin\b", None),
    ]),
    ("Yale spirit", [
        ("bulldogs", "Bulldogs", r"bulldog", None),
        ("the-game", "The Game (Harvard-Yale)", r"harvard", None),
        ("boola-boola", "Boola Boola", r"boola boola", None),
        ("yale-bowl", "Yale Bowl", r"yale bowl", None),
    ]),
]
_GROUP_RULES = {
    option_id: (re.compile(pattern, re.IGNORECASE), re.compile(skip, re.IGNORECASE) if skip else None)
    for _, options in GROUPS
    for option_id, _, pattern, skip in options
}


def category_of(product: Product) -> str | None:
    kind = product.garment_type.lower()
    return next((cid for cid, _, test in CATEGORIES if test.search(kind)), None)


def collections_of(product: Product) -> set[str]:
    """Every "shop for" option this product belongs to (a Berkeley hockey hoodie is in both)."""
    return {
        option_id
        for option_id, (pattern, skip) in _GROUP_RULES.items()
        if pattern.search(product.name) and not (skip and skip.search(product.name))
    }


def filter_products(products: list[Product], category: str | None = None, collection: str | None = None) -> list[Product]:
    if category:
        products = [p for p in products if category_of(p) == category]
    if collection:
        products = [p for p in products if collection in collections_of(p)]
    return products


def browse_filters(products: list[Product] | None = None) -> dict:
    """The options for the Products page dropdowns, each with how many products it holds (empty ones are left out)."""
    products = products if products is not None else load_products()
    by_category: dict[str, int] = {}
    by_collection: dict[str, int] = {}
    for p in products:
        by_category[category_of(p) or ""] = by_category.get(category_of(p) or "", 0) + 1
        for option_id in collections_of(p):
            by_collection[option_id] = by_collection.get(option_id, 0) + 1
    return {
        "categories": [{"id": cid, "label": label, "count": by_category[cid]} for cid, label, _ in CATEGORIES if by_category.get(cid)],
        "groups": [
            {"label": group, "options": [{"id": oid, "label": label, "count": by_collection[oid]} for oid, label, _, _ in options if by_collection.get(oid)]}
            for group, options in GROUPS
            if any(by_collection.get(oid) for oid, _, _, _ in options)
        ],
    }
