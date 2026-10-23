"""Tests for customer memory: who the chatbot is talking to, purchases, the saved conversation and the
"welcome back" question, feedback for admins, and what the chatbot knows about the page. They never call the
real AI service and run on a throwaway copy of the database.

    .venv/bin/pytest -q
"""

import sqlite3
from types import SimpleNamespace

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from test_auth import GOOD, NEW, _tmp, client, rows  # noqa: F401  (client is a fixture)

import admin  # noqa: E402
import agent  # noqa: E402
import auth  # noqa: E402
import feedback_report  # noqa: E402
import main  # noqa: E402
import memory  # noqa: E402
import pages  # noqa: E402
import tools  # noqa: E402
from models import AgentDeps, PageContext, PageState, User  # noqa: E402

HOODIE, TEE = "basic-hoodie-big-yale", "yale-sports-t-shirt-field-hockey"


def ctx(user=None, page=None, awaiting=None):
    return SimpleNamespace(deps=AgentDeps(user=user, page=page, awaiting_feedback=awaiting))


def sign_up(client, email="ana.lopez@example.com", first="Ana", last="Lopez") -> User:
    body = {**NEW, "email": email, "first_name": first, "last_name": last}
    return User(**client.post("/api/auth/register", json=body).json())


def buy(user_id: int, product_id: str, size="M", days_ago=10) -> int:
    """Put a purchase on a customer's account, dated `days_ago` days back. Returns the order item's id."""
    conn = sqlite3.connect(_tmp / "test.db")
    order = conn.execute("INSERT INTO orders (user_id, created_at) VALUES (?, ?)", (user_id, memory._days_ago(days_ago))).lastrowid
    item = conn.execute("INSERT INTO order_items (order_id, product_id, size) VALUES (?, ?, ?)", (order, product_id, size)).lastrowid
    conn.commit()
    conn.close()
    return item


def final(info, reply="ok", **extra):
    return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args={"reply": reply, **extra})])


@pytest.fixture(autouse=True)
def fresh():
    auth.reset_limits()
    main.guest_memory.clear()


def test_the_memory_tables_exist_after_startup(client):
    names = {r["name"] for r in rows("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}
    assert {"orders", "order_items", "customer_feedback", "product_feedback_summary", "chat_messages"} <= names


# ---------- who is chatting ----------
def test_about_me_gives_a_logged_in_customer_their_own_name_and_email_and_a_guest_nothing(client):
    ana = sign_up(client)
    me = tools.about_me(ctx(ana))
    assert (me.logged_in, me.first_name, me.last_name, me.email) == (True, "Ana", "Lopez", "ana.lopez@example.com")
    assert set(me.model_dump()) == {"logged_in", "first_name", "last_name", "email"}  # no phone, no address, no payment, no password
    guest = tools.about_me(ctx(None))
    assert guest.model_dump() == {"logged_in": False, "first_name": None, "last_name": None, "email": None}


# ---------- purchase history ----------
def test_purchase_history_is_the_customers_own_and_has_no_payment_details(client):
    ana = sign_up(client)
    buy(ana.id, HOODIE, "M", days_ago=30)
    buy(ana.id, TEE, "L", days_ago=5)
    history = tools.my_purchases(ctx(ana))
    assert [p.name for p in history.purchases] == ["Yale Sports T-Shirt Field Hockey", "Basic Hoodie Big Yale"]  # newest first
    assert history.purchases[0].size == "L" and history.purchases[0].feedback_status == "not_asked"
    assert set(history.purchases[0].model_dump()) == {"product_id", "name", "garment_type", "colors", "size", "quantity", "purchased_on", "feedback_status"}

    client.post("/api/auth/logout")
    ben = sign_up(client, "ben@example.com", "Ben", "Park")
    assert tools.my_purchases(ctx(ben)).purchases == []  # Ana's purchases are invisible to Ben
    guest = tools.my_purchases(ctx(None))
    assert guest.logged_in is False and guest.purchases == []


def test_the_agent_cannot_ask_for_someone_elses_history():
    import inspect

    for tool in (tools.my_purchases, tools.about_me):
        assert "user_id" not in inspect.signature(tool).parameters  # the customer comes from the login, never from the AI
    assert "user_id" not in inspect.signature(tools.record_feedback).parameters


# ---------- resuming the conversation, and asking how a purchase worked out ----------
def test_logging_back_in_resumes_the_conversation_and_asks_about_a_past_purchase(client):
    ana = sign_up(client)
    buy(ana.id, HOODIE, "M", days_ago=10)
    r = client.post("/api/chat/resume")
    body = r.json()
    assert r.status_code == 200 and body["follow_up"]["product_id"] == HOODIE
    question = body["messages"][-1]
    assert question["role"] == "assistant" and "Welcome back, Ana" in question["content"] and "Basic Hoodie Big Yale" in question["content"] and "size M" in question["content"]
    # it is part of the saved conversation, and it is only asked once
    assert rows("SELECT COUNT(*) AS n FROM chat_messages WHERE user_id = ? AND role = 'assistant' AND content LIKE '%worked out%'", ana.id)[0]["n"] == 1
    again = client.post("/api/chat/resume").json()
    assert again["follow_up"] is None and [m["content"] for m in again["messages"]].count(question["content"]) == 1
    assert tools.my_purchases(ctx(ana)).purchases[0].feedback_status == "asked"


def test_nothing_to_ask_about_when_the_purchase_is_too_new_too_old_or_there_are_none(client):
    ana = sign_up(client)
    assert client.post("/api/chat/resume").json() == {"messages": [], "follow_up": None}  # nothing bought yet
    buy(ana.id, HOODIE, days_ago=1)  # too recent to have been tried
    buy(ana.id, TEE, days_ago=400)  # too long ago to bother them with
    assert client.post("/api/chat/resume").json()["follow_up"] is None


def test_resume_needs_a_login(client):
    assert client.post("/api/chat/resume").status_code == 401


def test_the_conversation_is_still_there_after_logging_out_and_back_in(client):
    sign_up(client)
    with agent.get_agent().override(model=FunctionModel(lambda m, i: final(i, "Hi Ana! Hoodies are on the Products page."))):
        client.post("/api/chat", json={"message": "what should I wear to the game?"})
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": NEW["email"], "password": GOOD})
    msgs = client.post("/api/chat/resume").json()["messages"]
    assert [m["content"] for m in msgs] == ["what should I wear to the game?", "Hi Ana! Hoodies are on the Products page."]


def test_guests_chat_but_nothing_of_theirs_is_saved(client):
    before = rows("SELECT COUNT(*) AS n FROM chat_messages")[0]["n"]
    with agent.get_agent().override(model=FunctionModel(lambda m, i: final(i))):
        assert client.post("/api/chat", json={"message": "hi from a guest"}).status_code == 200
    assert rows("SELECT COUNT(*) AS n FROM chat_messages")[0]["n"] == before


# ---------- feedback ----------
def test_a_customers_answer_is_filed_as_feedback_by_the_agent(client):
    ana = sign_up(client)
    buy(ana.id, HOODIE, "M", days_ago=10)
    client.post("/api/chat/resume")  # the chatbot asks how it worked out
    seen = []

    def fake(messages, info):
        seen.append(messages[-1].instructions)
        if len(seen) == 1:
            return ModelResponse(parts=[ToolCallPart(tool_name="record_feedback", args={"product_id": HOODIE, "comment": "Love it, so warm.", "rating": 5, "fit": "true_to_size"})])
        return final(info, "So glad you love it, Ana!")

    with agent.get_agent().override(model=FunctionModel(fake)):
        r = client.post("/api/chat", json={"message": "honestly love it, so warm and fits perfectly"})
    assert "recently asked this customer how their Basic Hoodie Big Yale" in seen[0]  # the agent knows what the customer is answering
    assert r.json()["tools_used"] == ["record_feedback"]
    (fb,) = rows("SELECT * FROM customer_feedback")
    assert (fb["user_id"], fb["product_id"], fb["rating"], fb["fit"], fb["comment"]) == (ana.id, HOODIE, 5, "true_to_size", "Love it, so warm.")
    assert tools.my_purchases(ctx(ana)).purchases[0].feedback_status == "given"
    assert memory.awaiting_answer(ana.id) is None  # answered, so no longer pending


def test_feedback_can_only_be_filed_for_the_customers_own_purchases_and_is_checked(client):
    ana = sign_up(client)
    buy(ana.id, HOODIE)
    save = lambda **kw: tools.record_feedback(ctx(ana), **{"product_id": HOODIE, "comment": "Nice", **kw})  # noqa: E731
    assert save(product_id=TEE).saved is False  # never bought it
    assert save(comment="  ").saved is False and save(rating=6).saved is False and save(rating=0).saved is False
    assert tools.record_feedback(ctx(None), HOODIE, "Nice").saved is False  # guests can't leave feedback
    assert rows("SELECT COUNT(*) AS n FROM customer_feedback")[0]["n"] == 0

    assert save(rating=4).saved is True
    assert save(comment="Even better after a wash", rating=5).saved is True  # saying more updates the same entry
    (fb,) = rows("SELECT * FROM customer_feedback")
    assert (fb["rating"], fb["comment"]) == (5, "Even better after a wash")

    client.post("/api/auth/logout")
    ben = sign_up(client, "ben@example.com", "Ben", "Park")
    assert tools.record_feedback(ctx(ben), HOODIE, "I never bought this").saved is False  # not Ben's purchase


def test_admins_can_read_compiled_feedback_and_nobody_else_can(client, monkeypatch):
    ana = sign_up(client)
    buy(ana.id, HOODIE)
    buy(ana.id, TEE, days_ago=20)
    tools.record_feedback(ctx(ana), HOODIE, "Warm and soft", 5, "true_to_size")
    tools.record_feedback(ctx(ana), TEE, "Ran a bit small", 3, "runs_small")
    client.post("/api/auth/logout")
    ben = sign_up(client, "ben@example.com", "Ben", "Park")
    buy(ben.id, HOODIE)
    tools.record_feedback(ctx(ben), HOODIE, "Great", 4, "true_to_size")

    assert client.get("/api/admin/feedback").status_code == 403  # Ben is logged in but is not an admin
    client.post("/api/auth/logout")
    assert client.get("/api/admin/feedback").status_code == 401  # a guest isn't even logged in
    client.post("/api/auth/login", json={"email": NEW["email"], "password": GOOD})
    assert client.get("/api/admin/feedback").status_code == 403  # nobody is an admin until ADMIN_EMAILS names someone

    monkeypatch.setattr(admin, "ADMIN_EMAILS", {"ana.lopez@example.com"})
    entries = client.get("/api/admin/feedback").json()
    assert len(entries) == 3 and entries[0]["customer"] == "Ben P."
    assert not any("example.com" in str(e) for e in entries)  # no emails in the report
    summary = {s["product_id"]: s for s in client.get("/api/admin/feedback/summary").json()}
    assert summary[HOODIE]["responses"] == 2 and summary[HOODIE]["average_rating"] == 4.5 and summary[HOODIE]["true_to_size"] == 2
    assert summary[TEE]["runs_small"] == 1


def test_the_admin_report_compiles_everything_customers_said(client):
    assert "No feedback yet" in feedback_report.build_report()
    ana = sign_up(client)
    buy(ana.id, HOODIE)
    tools.record_feedback(ctx(ana), HOODIE, "Warm and soft", 5, "true_to_size")
    report = feedback_report.build_report()
    assert "Basic Hoodie Big Yale" in report and "Warm and soft" in report and "★★★★★" in report and "Ana L." in report
    assert "ana.lopez@example.com" not in report


# ---------- the page the customer is looking at ----------
def test_the_page_context_is_checked_against_the_database():
    ok = pages.build_context(PageState(path="/products/basic-hoodie-big-yale", selected_size="m", shown_product_ids=[HOODIE, "made-up"]))
    assert (ok.kind, ok.product_id, ok.selected_size, ok.shown_product_ids) == ("product", HOODIE, "M", [HOODIE])
    assert pages.build_context(PageState(path="/products/not-a-product")).kind == "other"
    assert pages.build_context(PageState(path="/products/../../etc/passwd")).product_id is None
    assert pages.build_context(PageState(path="/products/" + HOODIE, selected_size="HUGE")).selected_size is None
    assert pages.build_context(PageState(path="/about/")).kind == "about"
    assert pages.build_context(None) is None


def test_the_agent_can_see_the_product_page_the_customer_is_on_with_live_data(client):
    page = PageContext(kind="product", path=f"/products/{HOODIE}", product_id=HOODIE, selected_size="S", shown_product_ids=[TEE])
    conn = sqlite3.connect(_tmp / "test.db")
    conn.execute("UPDATE inventory SET quantity = 0 WHERE product_id = ? AND size = 'S'", (HOODIE,))
    conn.commit()
    conn.close()
    info = tools.about_this_page(ctx(page=page))
    assert info.kind == "product" and info.product.name == "Basic Hoodie Big Yale" and info.product.price == 68.0
    assert info.selected_size_check.status == "sold_out" and info.selected_size_check.next_size_up.size == "M"  # the size they picked is gone: the nearest are offered
    assert [p.product_id for p in info.cards_on_page] == [TEE]
    home = tools.about_this_page(ctx(page=PageContext(kind="home", path="/")))
    assert home.product is None and "home page" in home.description
    assert tools.about_this_page(ctx()).kind == "other"  # no page information


def test_the_chat_route_passes_the_page_into_the_agents_instructions(client):
    seen = []

    def fake(messages, info):
        seen.append(messages[-1].instructions)
        return final(info)

    with agent.get_agent().override(model=FunctionModel(fake)):
        client.post("/api/chat", json={"message": "is this in stock in medium?", "page": {"path": f"/products/{HOODIE}", "selected_size": "M"}})
        client.post("/api/chat", json={"message": "hi", "page": {"path": "/products/definitely-fake"}})
        client.post("/api/chat", json={"message": "hi"})
    assert "Basic Hoodie Big Yale" in seen[0] and HOODIE in seen[0] and "size M chosen" in seen[0] and "about_this_page" in seen[0]
    assert "Basic Hoodie Big Yale" not in seen[1]  # an invented product page isn't believed
    assert "The customer is looking at" in seen[0] and "The customer is looking at" in seen[1]  # a real page line (the second is "a page of the website")
    assert "The customer is looking at" not in seen[2]  # no page given, so the agent isn't told one


def test_the_chat_route_rejects_oversized_page_details(client):
    assert client.post("/api/chat", json={"message": "hi", "page": {"path": "x" * 500}}).status_code == 422
    assert client.post("/api/chat", json={"message": "hi", "page": {"path": "/", "shown_product_ids": ["a"] * 20}}).status_code == 422


# ---------- the prompt ----------
def test_the_prompt_explains_memory_page_and_feedback_rules():
    text = agent.PROMPT_FILE.read_text().lower()
    for must_say in [
        "own email address",  # may see the customer's own email
        "no phone numbers or home or mailing addresses",  # but nothing else
        "my_purchases",
        "only to make good recommendations",
        "the page the customer is on",
        "about_this_page",
        "following up on a past purchase",
        "record_feedback",
        "only if they clearly gave or implied one",  # no guessed ratings
        "never make up feedback",
        "a guest",
    ]:
        assert must_say in text, must_say


def test_mentioning_something_the_customer_already_bought_does_not_put_it_on_the_page(client):
    ana = sign_up(client)
    buy(ana.id, HOODIE, days_ago=30)
    calls = []

    def fake(messages, info):
        calls.append(1)
        if len(calls) == 1:
            return ModelResponse(parts=[ToolCallPart(tool_name="my_purchases", args={})])
        if len(calls) == 2:
            return ModelResponse(parts=[ToolCallPart(tool_name="search_products", args={"query": "yale uncle hoodie"})])
        return final(info, "Since you own the Basic Hoodie Big Yale, try the Yale Uncle Hoodie.", product_ids=["yale-uncle-hoodie"], results_title="More hoodies")

    with agent.get_agent().override(model=FunctionModel(fake)):
        items = client.post("/api/chat", json={"message": "what next?"}).json()["results"]["items"]
    assert [i["product_id"] for i in items] == ["yale-uncle-hoodie"]  # the one they already own isn't added


def test_an_older_orders_table_is_upgraded_without_losing_anything(client):
    conn = sqlite3.connect(_tmp / "test.db")
    conn.executescript("DROP VIEW product_feedback_summary; DROP TABLE customer_feedback; DROP TABLE order_items; DROP TABLE orders;"
                       "CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')));"
                       "INSERT INTO orders (user_id) VALUES (1);")
    conn.commit()
    conn.close()
    memory.ensure_tables()  # what happens every time the API starts
    columns = {r["name"] for r in rows("PRAGMA table_info(orders)")}
    assert "note" in columns and rows("SELECT COUNT(*) AS n FROM orders")[0]["n"] == 1
