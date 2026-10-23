"""Gift certificates: parents and loved ones buy a digital gift card for a student, and the student shops with it
and gets 10% off everything they pay for with it.

  POST /api/gift-cards/buy        anyone (no account needed) orders a gift certificate; the code is emailed to the recipient
  POST /api/gift-cards/check      is this code real, and how much is left on it?
  POST /api/gift-cards/quote      what would this cart cost, with 10% off? (no money moves)
  POST /api/checkout/gift-card    a logged-in customer pays for their cart with a gift card: stock is reduced, the
                                  purchase is saved on their account, and the balance goes down

IMPORTANT: this is a class project with NO payment processing. Buying a gift certificate collects no card details and
charges nothing, and the website says so. Everything after that (the code, the balance, the 10% off, the purchase) is real.

A gift card's code is a secret, like a password, so only a fingerprint of it is stored. It is shown once to the buyer
and emailed to the recipient.
"""

import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request

import auth
import catalogue
import security
from emailer import send_email
from models import (
    GiftCardOrder,
    GiftCardPurchased,
    GiftCardStatus,
    GiftCheckout,
    GiftCodeCheck,
    GiftQuote,
    GiftReceipt,
    QuoteLine,
    User,
)

router = APIRouter(prefix="/api", tags=["gift certificates"])

DISCOUNT_PERCENT = 10
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, which are easy to misread
EMAIL = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]{2,}$")
NAME = re.compile(r"^[^\d<>{}\[\]\\/@;=$|]{1,50}$")
PAYMENT_NOTE = "This is a class project, so no payment is taken and no card details are collected. The gift certificate is real in this shop."


def ensure_tables() -> None:
    with auth.db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS gift_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_hash TEXT NOT NULL UNIQUE,
                code_last4 TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0),
                purchaser_name TEXT NOT NULL,
                purchaser_email TEXT NOT NULL,
                recipient_name TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS gift_card_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gift_card_id INTEGER NOT NULL,
                order_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                discount_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (gift_card_id) REFERENCES gift_cards(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );
            """
        )


def _normalize(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def _new_code() -> str:
    raw = "".join(secrets.choice(ALPHABET) for _ in range(12))
    return f"CC-{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def _dollars(cents: int) -> float:
    return round(cents / 100, 2)


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _card(conn, code: str):
    return conn.execute("SELECT * FROM gift_cards WHERE code_hash = ?", (security.hash_token(_normalize(code)),)).fetchone()


# ---------- buying ----------
@router.post("/gift-cards/buy", response_model=GiftCardPurchased, status_code=201)
def buy(order: GiftCardOrder, request: Request):
    wait = auth.throttle(f"gift-buy:{_ip(request)}", 10)
    if wait:
        raise HTTPException(429, f"That's a lot of gift certificates! Please wait about {wait} minute{'s' if wait != 1 else ''} and try again.")
    for label, value, pattern in [
        ("your name", order.purchaser_name, NAME),
        ("the recipient's name", order.recipient_name, NAME),
        ("your email", order.purchaser_email.strip(), EMAIL),
        ("the recipient's email", order.recipient_email.strip(), EMAIL),
    ]:
        if not pattern.match(value.strip()):
            raise HTTPException(422, {"message": f"Please check {label}.", "rules": []})
    message = " ".join(order.message.split())
    code = _new_code()
    with auth.db() as conn:
        conn.execute(
            "INSERT INTO gift_cards (code_hash, code_last4, amount_cents, balance_cents, purchaser_name, purchaser_email, recipient_name, recipient_email, message) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (security.hash_token(_normalize(code)), code[-4:], order.amount * 100, order.amount * 100,
             order.purchaser_name.strip(), order.purchaser_email.strip().lower(), order.recipient_name.strip(), order.recipient_email.strip().lower(), message),
        )
    note = f'\n\nA note from {order.purchaser_name.strip()}: "{message}"' if message else ""
    send_email(
        order.recipient_email.strip().lower(),
        f"{order.purchaser_name.strip()} sent you a Campus Customs gift certificate",
        f"Hi {order.recipient_name.strip()},\n\n{order.purchaser_name.strip()} sent you a ${order.amount} gift certificate for Campus Customs, "
        f"Yale's original licensed merchandise boutique.{note}\n\nYour code: {code}\n\n"
        f"How to use it: put things in your cart, open the cart, enter the code, and pay with your gift certificate. "
        f"Everything you buy with it is {DISCOUNT_PERCENT}% off.\n\nLux et Veritas,\nCampus Customs",
    )
    send_email(
        order.purchaser_email.strip().lower(),
        "Your Campus Customs gift certificate",
        f"Hi {order.purchaser_name.strip()},\n\nYour ${order.amount} gift certificate for {order.recipient_name.strip()} is ready, and we emailed it to "
        f"{order.recipient_email.strip().lower()}. (Code ending {code[-4:]}.)\n\n{PAYMENT_NOTE}\n\nCampus Customs",
    )
    return GiftCardPurchased(code=code, amount=order.amount, recipient_name=order.recipient_name.strip(), recipient_email=order.recipient_email.strip().lower(), payment_note=PAYMENT_NOTE)


# ---------- checking a code ----------
@router.post("/gift-cards/check", response_model=GiftCardStatus)
def check(body: GiftCodeCheck, request: Request):
    """Same answer for a wrong code as for a used-up one, and guessing is limited, so codes can't be farmed."""
    if auth.throttle(f"gift-check:{_ip(request)}", 20):
        raise HTTPException(429, "Too many tries. Please wait a few minutes and try again.")
    with auth.db() as conn:
        card = _card(conn, body.code)
    if not card or card["balance_cents"] <= 0:
        return GiftCardStatus(valid=False, discount_percent=DISCOUNT_PERCENT)
    return GiftCardStatus(valid=True, last4=card["code_last4"], balance=_dollars(card["balance_cents"]), discount_percent=DISCOUNT_PERCENT)


# ---------- pricing a cart ----------
def _price(items, conn, balance_cents: int) -> tuple[list[QuoteLine], int, int, int]:
    """Real prices from the database, never from the browser. Returns the lines, subtotal, discount and total in cents."""
    merged: dict[tuple[str, str], int] = {}
    for it in items:
        key = (it.product_id, it.size.strip().upper())
        merged[key] = merged.get(key, 0) + it.quantity
    products = {p.product_id: p for p in catalogue.load_products()}
    lines, subtotal = [], 0
    for (product_id, size), quantity in merged.items():
        product = products.get(product_id)
        stock = next((s.quantity for s in product.sizes if s.size == size), None) if product else None
        if product is None or stock is None:
            raise HTTPException(422, {"message": "One of the items in your cart isn't available any more.", "rules": []})
        if quantity > stock:
            raise HTTPException(409, {"message": f"Only {stock} of the {product.name} in size {size} {'is' if stock == 1 else 'are'} left.", "rules": []})
        unit = round(product.price * 100)
        lines.append(QuoteLine(product_id=product_id, name=product.name, size=size, quantity=quantity, unit_price=product.price, line_total=_dollars(unit * quantity)))
        subtotal += unit * quantity
    discount = (subtotal * DISCOUNT_PERCENT + 50) // 100  # 10%, rounded to the nearest cent
    return lines, subtotal, discount, subtotal - discount


def _quote(lines, subtotal, discount, total, balance_cents) -> dict:
    return dict(
        lines=lines, subtotal=_dollars(subtotal), discount_percent=DISCOUNT_PERCENT, discount=_dollars(discount),
        total=_dollars(total), balance=_dollars(balance_cents), enough=balance_cents >= total,
    )


@router.post("/gift-cards/quote", response_model=GiftQuote)
def quote(body: GiftCheckout, request: Request):
    if auth.throttle(f"gift-check:{_ip(request)}", 20):
        raise HTTPException(429, "Too many tries. Please wait a few minutes and try again.")
    with auth.db() as conn:
        card = _card(conn, body.code)
        if not card or card["balance_cents"] <= 0:
            raise HTTPException(404, {"message": "That gift certificate code wasn't found, or it has no balance left.", "rules": []})
        lines, subtotal, discount, total = _price(body.items, conn, card["balance_cents"])
    return GiftQuote(**_quote(lines, subtotal, discount, total, card["balance_cents"]))


# ---------- paying with a gift card ----------
@router.post("/checkout/gift-card", response_model=GiftReceipt)
def pay_with_gift_card(body: GiftCheckout, request: Request, user: User = Depends(auth.current_user)):
    """All or nothing: if anything fails (not enough balance, an item sold out meanwhile), nothing changes."""
    if auth.throttle(f"gift-check:{_ip(request)}", 20):
        raise HTTPException(429, "Too many tries. Please wait a few minutes and try again.")
    with auth.db() as conn:
        card = _card(conn, body.code)
        if not card or card["balance_cents"] <= 0:
            raise HTTPException(404, {"message": "That gift certificate code wasn't found, or it has no balance left.", "rules": []})
        lines, subtotal, discount, total = _price(body.items, conn, card["balance_cents"])
        if total > card["balance_cents"]:
            raise HTTPException(402, {"message": f"This gift certificate has ${_dollars(card['balance_cents']):,.2f} left, but the order comes to ${_dollars(total):,.2f} after 10% off.", "rules": []})
        order = conn.execute("INSERT INTO orders (user_id, note) VALUES (?, 'paid with a gift certificate')", (user.id,)).lastrowid
        for line in lines:
            took = conn.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE product_id = ? AND size = ? AND quantity >= ?",
                (line.quantity, line.product_id, line.size, line.quantity),
            ).rowcount
            if not took:  # someone else bought the last one a moment ago
                raise HTTPException(409, {"message": f"Sorry, the {line.name} in size {line.size} just sold out.", "rules": []})
            conn.execute("INSERT INTO order_items (order_id, product_id, size, quantity) VALUES (?, ?, ?, ?)", (order, line.product_id, line.size, line.quantity))
        remaining = card["balance_cents"] - total
        conn.execute("UPDATE gift_cards SET balance_cents = ? WHERE id = ?", (remaining, card["id"]))
        conn.execute("INSERT INTO gift_card_uses (gift_card_id, order_id, amount_cents, discount_cents) VALUES (?, ?, ?, ?)", (card["id"], order, total, discount))
    return GiftReceipt(**_quote(lines, subtotal, discount, total, card["balance_cents"]), order_id=order, balance_remaining=_dollars(remaining))
