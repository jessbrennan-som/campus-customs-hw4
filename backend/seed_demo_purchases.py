"""OPTIONAL: adds two demo purchases to ONE customer's account, so you can try the chatbot's "how did it work out?"
follow-up and its purchase-based recommendations. The shop has no checkout yet, so there is otherwise no purchase
history to try. The purchases are made-up demo data, dated 12 and 40 days ago.

    cd backend
    source .venv/bin/activate
    python seed_demo_purchases.py you@example.com          # use the email of an account you made on the site
    python seed_demo_purchases.py you@example.com --undo   # remove the demo purchases (and any feedback on them) again
"""

import argparse

import auth
import memory

DEMO = [("basic-hoodie-big-yale", "M", 12), ("yale-sports-t-shirt-field-hockey", "L", 40)]
MARK = "demo purchase"  # stored on the order so --undo can find exactly these rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("--undo", action="store_true")
    args = parser.parse_args()
    memory.ensure_tables()
    with auth.db() as conn:
        user = conn.execute("SELECT id, first_name FROM users WHERE email = ?", (args.email.strip().lower(),)).fetchone()
        if not user:
            raise SystemExit(f"No account with the email {args.email}. Create one on the site first.")
        if args.undo:
            conn.execute("DELETE FROM customer_feedback WHERE order_item_id IN (SELECT i.id FROM order_items i JOIN orders o ON o.id = i.order_id WHERE o.user_id = ? AND o.note = ?)", (user["id"], MARK))
            conn.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id = ? AND note = ?)", (user["id"], MARK))
            conn.execute("DELETE FROM orders WHERE user_id = ? AND note = ?", (user["id"], MARK))
            print(f"Removed the demo purchases for {args.email}.")
            return
        for product_id, size, days_ago in DEMO:
            when = memory._days_ago(days_ago)
            order = conn.execute("INSERT INTO orders (user_id, created_at, note) VALUES (?, ?, ?)", (user["id"], when, MARK)).lastrowid
            conn.execute("INSERT INTO order_items (order_id, product_id, size, quantity) VALUES (?, ?, ?, 1)", (order, product_id, size))
    print(f"Added {len(DEMO)} demo purchases for {args.email}. Open the chat while logged in as that customer.")


if __name__ == "__main__":
    main()
