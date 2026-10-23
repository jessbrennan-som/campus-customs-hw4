"""Customer memory: what the shop remembers about a logged-in customer, for the chatbot and for admins.

  chat_messages      every message of a logged-in customer's chat (created in the original database; this file only
                     writes the chatbot's "welcome back" question into it)
  orders, order_items  what the customer bought (so the chatbot can recommend, and ask how a purchase worked out)
  customer_feedback  what customers said about products they bought, for admins to read later
  product_feedback_summary  a ready-made view: one line per product with the count and the average rating

Every function that reads or writes one customer's data takes `user_id`. The chatbot's tools get that id from the
logged-in session (AgentDeps), never from anything the AI types, so the AI cannot ask for another customer's data.
"""

import json
from datetime import datetime, timedelta, timezone

import auth
from models import FeedbackSaved, FollowUp, PurchaseInfo

FEEDBACK_AFTER_DAYS = 3  # ask how a purchase worked out once it has had this long to arrive and be tried
ASK_WITHIN_DAYS = 90  # ...but don't dig up purchases older than this
ANSWER_WINDOW_DAYS = 14  # a question the customer hasn't answered stays "open" for this long
FIT_VALUES = ("runs_small", "true_to_size", "runs_large")


def ensure_tables() -> None:
    """Creates the purchase and feedback tables if they aren't there yet. Safe to run on every start."""
    with auth.db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                note TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                size TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                feedback_asked_at TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES catalogue(product_id)
            );
            CREATE TABLE IF NOT EXISTS customer_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                order_item_id INTEGER UNIQUE,
                rating INTEGER CHECK (rating BETWEEN 1 AND 5),
                fit TEXT CHECK (fit IN ('runs_small', 'true_to_size', 'runs_large')),
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES catalogue(product_id),
                FOREIGN KEY (order_item_id) REFERENCES order_items(id)
            );
            CREATE VIEW IF NOT EXISTS product_feedback_summary AS
                SELECT f.product_id AS product_id,
                       c.name AS product_name,
                       COUNT(*) AS responses,
                       ROUND(AVG(f.rating), 2) AS average_rating,
                       SUM(f.fit = 'runs_small') AS runs_small,
                       SUM(f.fit = 'true_to_size') AS true_to_size,
                       SUM(f.fit = 'runs_large') AS runs_large,
                       MAX(f.created_at) AS latest
                FROM customer_feedback f JOIN catalogue c ON c.product_id = f.product_id
                GROUP BY f.product_id;
            """
        )
        # A table made by an earlier version of this code may be missing newer columns, and CREATE TABLE IF NOT
        # EXISTS won't add them. Add any that are missing, so upgrading never needs the database rebuilt.
        have = {r["name"] for r in conn.execute("PRAGMA table_info(orders)")}
        if "note" not in have:
            conn.execute("ALTER TABLE orders ADD COLUMN note TEXT")


def _days_ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---------- a customer's purchases ----------
def purchases(user_id: int, limit: int = 20) -> list[PurchaseInfo]:
    """What this customer bought, newest first: product facts and dates, never anything about payment."""
    with auth.db() as conn:
        rows = conn.execute(
            """
            SELECT i.id, i.product_id, i.size, i.quantity, i.feedback_asked_at, o.created_at,
                   c.name, c.garment_type, c.colors,
                   EXISTS (SELECT 1 FROM customer_feedback f WHERE f.order_item_id = i.id) AS has_feedback
            FROM order_items i
            JOIN orders o ON o.id = i.order_id
            JOIN catalogue c ON c.product_id = i.product_id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC, i.id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [
        PurchaseInfo(
            product_id=r["product_id"],
            name=r["name"],
            garment_type=r["garment_type"],
            colors=json.loads(r["colors"]),
            size=r["size"],
            quantity=r["quantity"],
            purchased_on=r["created_at"][:10],
            feedback_status="given" if r["has_feedback"] else "asked" if r["feedback_asked_at"] else "not_asked",
        )
        for r in rows
    ]


def _follow_up_from(row, first_name: str = "") -> FollowUp:
    greeting = f"Welcome back, {first_name}! " if first_name else "Welcome back! "
    return FollowUp(
        order_item_id=row["id"],
        product_id=row["product_id"],
        product_name=row["name"],
        size=row["size"],
        question=f"{greeting}The last time you were here you picked up the {row['name']} in size {row['size']}. How has it worked out for you?",
    )


_ITEM_SQL = """
    SELECT i.id, i.product_id, i.size, c.name
    FROM order_items i
    JOIN orders o ON o.id = i.order_id
    JOIN catalogue c ON c.product_id = i.product_id
    WHERE o.user_id = ?
      AND NOT EXISTS (SELECT 1 FROM customer_feedback f WHERE f.order_item_id = i.id)
"""


def follow_up_due(user_id: int, first_name: str = "") -> FollowUp | None:
    """The most recent purchase that has had time to be tried, hasn't been asked about, and has no feedback yet."""
    with auth.db() as conn:
        # one open question at a time: don't pile a second on top of one the customer hasn't answered
        waiting = conn.execute(_ITEM_SQL + " AND i.feedback_asked_at IS NOT NULL AND i.feedback_asked_at > ?", (user_id, _days_ago(ANSWER_WINDOW_DAYS))).fetchone()
        if waiting:
            return None
        row = conn.execute(
            _ITEM_SQL + " AND i.feedback_asked_at IS NULL AND o.created_at <= ? AND o.created_at >= ? ORDER BY o.created_at DESC, i.id DESC LIMIT 1",
            (user_id, _days_ago(FEEDBACK_AFTER_DAYS), _days_ago(ASK_WITHIN_DAYS)),
        ).fetchone()
    return _follow_up_from(row, first_name) if row else None


def awaiting_answer(user_id: int) -> FollowUp | None:
    """A purchase the chatbot asked about recently and the customer hasn't given feedback on yet."""
    with auth.db() as conn:
        row = conn.execute(
            _ITEM_SQL + " AND i.feedback_asked_at IS NOT NULL AND i.feedback_asked_at > ? ORDER BY i.feedback_asked_at DESC LIMIT 1",
            (user_id, _days_ago(ANSWER_WINDOW_DAYS)),
        ).fetchone()
    return _follow_up_from(row) if row else None


def mark_asked(order_item_id: int) -> None:
    with auth.db() as conn:
        conn.execute("UPDATE order_items SET feedback_asked_at = ? WHERE id = ?", (_now(), order_item_id))


# ---------- feedback ----------
def save_feedback(user_id: int, product_id: str, comment: str, rating: int | None = None, fit: str | None = None) -> FeedbackSaved:
    """Files what a customer said about a product they bought. Only products this customer really bought can be
    reviewed, and each purchase has one feedback entry (saying more later updates it)."""
    comment = " ".join(comment.split())[:500]
    if not comment:
        return FeedbackSaved(saved=False, message="There was no comment to save.")
    if rating is not None and not 1 <= rating <= 5:
        return FeedbackSaved(saved=False, message="The rating must be a whole number from 1 to 5.")
    if fit is not None and fit not in FIT_VALUES:
        return FeedbackSaved(saved=False, message=f"fit must be one of {', '.join(FIT_VALUES)}.")
    with auth.db() as conn:
        item = conn.execute(
            """
            SELECT i.id, c.name FROM order_items i
            JOIN orders o ON o.id = i.order_id
            JOIN catalogue c ON c.product_id = i.product_id
            WHERE o.user_id = ? AND i.product_id = ?
            ORDER BY (SELECT COUNT(*) FROM customer_feedback f WHERE f.order_item_id = i.id), o.created_at DESC
            LIMIT 1
            """,
            (user_id, product_id),
        ).fetchone()
        if not item:
            return FeedbackSaved(saved=False, message="That product isn't in this customer's purchases, so feedback can't be saved for it.")
        existing = conn.execute("SELECT id FROM customer_feedback WHERE order_item_id = ?", (item["id"],)).fetchone()
        if existing:
            conn.execute(
                "UPDATE customer_feedback SET rating = COALESCE(?, rating), fit = COALESCE(?, fit), comment = ?, created_at = ? WHERE id = ?",
                (rating, fit, comment, _now(), existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO customer_feedback (user_id, product_id, order_item_id, rating, fit, comment) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, product_id, item["id"], rating, fit, comment),
            )
        conn.execute("UPDATE order_items SET feedback_asked_at = COALESCE(feedback_asked_at, ?) WHERE id = ?", (_now(), item["id"]))
    return FeedbackSaved(saved=True, product_name=item["name"], message=f"Saved the customer's feedback on the {item['name']}.")


# ---------- for admins ----------
def all_feedback(limit: int = 200) -> list[dict]:
    """Every feedback entry, newest first. The customer is shown as a first name and last initial only."""
    with auth.db() as conn:
        rows = conn.execute(
            """
            SELECT f.id, f.product_id, c.name AS product_name, u.first_name, u.last_name, f.rating, f.fit, f.comment, f.created_at
            FROM customer_feedback f
            JOIN catalogue c ON c.product_id = f.product_id
            JOIN users u ON u.id = f.user_id
            ORDER BY f.created_at DESC, f.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "product_id": r["product_id"],
            "product_name": r["product_name"],
            "customer": f"{r['first_name'] or 'Customer'} {(r['last_name'] or '')[:1]}.".replace(" .", ""),
            "rating": r["rating"],
            "fit": r["fit"],
            "comment": r["comment"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def feedback_summary() -> list[dict]:
    """One line per product: how many people answered, the average rating, and how it fits."""
    with auth.db() as conn:
        rows = conn.execute("SELECT * FROM product_feedback_summary ORDER BY responses DESC, product_name").fetchall()
    return [dict(r) for r in rows]
