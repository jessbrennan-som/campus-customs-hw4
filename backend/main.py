"""Campus Customs API: the shop, customer accounts, and the chatbot.

Run from this folder:   .venv/bin/uvicorn main:app --port 8000 --reload
Interactive docs:       http://localhost:8000/docs

How the files fit together:
  main.py        the web routes (this file)
  models.py      the Pydantic types: products, chat messages, the agent's answer, tool results
  catalogue.py   reads products and stock from the database
  auth.py        accounts: create account, log in, reset and change password
  agent.py       the chatbot (a PydanticAI agent) and how it's wired up
  tools.py       what the chatbot can look up
  prompt/prompt.md   the chatbot's instructions
"""

import json
import logging
import re
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

import admin
import agent
import auth
import catalogue
import giftcards
import lessons
import memory
import pages
from config import ALLOWED_ORIGINS, DB_PATH, IMAGE_DIR, WHITE_DIR
from models import AgentDeps, ChatHistory, ChatRequest, ChatResponse, ChatTurn, IdleRequest, Product, ProductResult, SearchResults, SimilarProduct, User

log = logging.getLogger("campus-customs")


@asynccontextmanager
async def lifespan(_: FastAPI):
    auth.ensure_tables()  # the sessions and password-reset tables that accounts need
    memory.ensure_tables()  # purchases and customer feedback
    giftcards.ensure_tables()  # gift certificates
    lessons.ensure_tables()  # what the chatbot has learned from mistakes
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)

# The React app (port 5173) and this API (port 8000) are different origins; CORS lets the browser call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,  # lets the browser send the login cookie
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(giftcards.router)


# ---------- photos ----------
@app.get("/images/{filename}")
def product_image(filename: str):
    """A product photo. The database stores paths like "products/basic-hoodie-big-yale.jpg"; the web
    address of that photo is /images/basic-hoodie-big-yale.jpg. The white-background copy is served
    when there is one, otherwise the original."""
    for folder in (WHITE_DIR, IMAGE_DIR):
        path = folder / filename
        if path.parent == folder and path.is_file():
            return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"})
    raise HTTPException(404, "No such image")


# ---------- the shop ----------
@app.get("/api/health")
def health():
    return {"status": "ok", "products": len(catalogue.load_products())}


@app.get("/api/products", response_model=list[Product])
def list_products(
    search: str | None = Query(None, description="words to look for in the name, type, description, colors and tags"),
    garment_type: str | None = Query(None, description="exact garment type, e.g. 'pullover hoodie'"),
    category: str | None = Query(None, description="a category id from /api/browse-filters, like 'hoodies' or 'jackets'"),
    collection: str | None = Query(None, description="a 'shop for' id from /api/browse-filters, like 'berkeley', 'hockey' or 'mom'"),
):
    products = catalogue.filter_products(catalogue.load_products(), category, collection)
    if garment_type:
        products = [p for p in products if p.garment_type == garment_type]
    if search:
        words = re.findall(r"[a-z0-9']+", search.lower())

        def haystack(p: Product) -> str:
            return " ".join([p.name, p.garment_type, p.description, *p.colors, *p.search_tags]).lower()

        products = [p for p in products if all(w in haystack(p) for w in words)]
    return products


@app.get("/api/browse-filters")
def browse_filters():
    """The options for the Products page dropdowns: categories (Hoodies, T-shirts, Jackets...) and "shop for"
    groups (residential colleges, schools, sports, family, Yale spirit), each with how many products it has."""
    return catalogue.browse_filters()


@app.get("/api/garment-types")
def garment_types() -> list[dict]:
    """Garment types with how many products each has, for the filter menu."""
    counts: dict[str, int] = {}
    for p in catalogue.load_products():
        counts[p.garment_type] = counts.get(p.garment_type, 0) + 1
    return [{"garment_type": g, "count": n} for g, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def _product_or_404(product_id: str) -> Product:
    product = catalogue.find_product(product_id)
    if product is None:
        raise HTTPException(404, f"No product '{product_id}'")
    return product


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: str):
    return _product_or_404(product_id)


@app.get("/api/products/{product_id}/similar", response_model=list[SimilarProduct])
def similar_products(
    product_id: str,
    size: str | None = Query(None, description="the size the shopper is looking at, if any"),
    limit: int = Query(3, ge=1, le=12),
):
    """Other products that match this one's style, color or size, best match first."""
    return catalogue.similar_to(_product_or_404(product_id), size, limit)


# ---------- the chatbot ----------
CHAT_LIMIT = 30  # messages per person every 15 minutes, so nobody can run up the AI bill
HISTORY_MESSAGES = 12  # how much of a logged-in customer's past chat the agent sees
GUEST_MESSAGES = 30  # how much of a guest's current chat the agent remembers
MAX_GUESTS = 500
guest_memory: dict[str, list[ModelMessage]] = {}  # guests' conversations live in memory only


def _short_info(description: str, limit: int = 110) -> str:
    """The first sentence of a description, trimmed to fit on a card."""
    text = " ".join(description.split())
    # end the sentence at a real full stop (a lowercase letter or number before it), not at "EST." or "U.S."
    first = re.split(r"(?<=[a-z0-9)][.!?])\s+(?=[A-Z])", text, maxsplit=1)[0]
    if len(first) <= limit:
        return first
    return first[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _search_results(product_ids: list[str], title: str | None) -> SearchResults | None:
    """The page cards for the products the agent chose. Every field is read from the database by product id,
    so what appears on the page is the real name, price, photo and stock, whatever the AI's words said."""
    by_id = {p.product_id: p for p in catalogue.load_products()}
    items = [
        ProductResult(
            product_id=p.product_id,
            name=p.name,
            garment_type=p.garment_type,
            price=p.price,
            price_text=f"${p.price:,.2f}",
            image_url=p.image_url,
            short_info=_short_info(p.description),
            colors=p.colors,
            in_stock=p.total_stock > 0,
        )
        for p in (by_id.get(i) for i in product_ids)
        if p is not None
    ]
    return SearchResults(title=(title or "").strip() or "Picks from Handsome Dan", items=items) if items else None


def _saved_chat(user_id: int, limit: int) -> list[sqlite3.Row]:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT role, content, products_json FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    finally:
        conn.close()
    return list(reversed(rows))


def _save_chat(user_id: int, question: str, reply: str, results: SearchResults | None) -> None:
    """A logged-in customer's chat is kept in the chat_messages table, with the products the chatbot showed."""
    shown = json.dumps([{"product_id": c.product_id, "name": c.name, "garment_type": c.garment_type, "price": c.price} for c in results.items]) if results else None
    with auth.db() as conn:
        conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, question))
        conn.execute("INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)", (user_id, reply, shown))


def _as_messages(rows: list[sqlite3.Row]) -> list[ModelMessage]:
    return [
        ModelRequest(parts=[UserPromptPart(content=r["content"])]) if r["role"] == "user" else ModelResponse(parts=[TextPart(content=r["content"])])
        for r in rows
        if r["role"] in ("user", "assistant")
    ]


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, user: User | None = Depends(auth.optional_user)):
    """One message from the website in, one reply from the shop chatbot out, plus (in `results`) the product
    cards the website should show on the page the customer is looking at.

    Logged-in customers get their past conversation remembered (it is saved in chat_messages) and are
    greeted by name. Guests are remembered for the current visit only.
    """
    ip = request.client.host if request.client else "unknown"
    wait = auth.throttle(f"chat:{f'user:{user.id}' if user else f'ip:{ip}'}", CHAT_LIMIT)
    if wait:
        raise HTTPException(429, f"You're chatting a lot! Please give me about {wait} minute{'s' if wait != 1 else ''} and ask again.")

    guest_key = f"{ip}:{body.session_id or ''}"
    history = _as_messages(_saved_chat(user.id, HISTORY_MESSAGES)) if user else guest_memory.get(guest_key, [])
    question = body.message.strip()
    try:
        deps = AgentDeps(
            user=user,
            page=pages.build_context(body.page),  # which page they're on, checked against the database
            awaiting_feedback=memory.awaiting_answer(user.id) if user else None,  # a purchase we just asked about
            visitor_key=f"user:{user.id}" if user else guest_key,
            lessons=lessons.matching(question),  # what past customers taught us about words in this message
        )
        result = await agent.chat(question, history, deps)
    except agent.NotConfigured as e:
        raise HTTPException(503, "The shop assistant isn't set up yet (it needs an API key).") from e
    except Exception as e:  # the AI service or network failed; tell the website politely
        log.exception("chat failed")
        raise HTTPException(502, "Handsome Dan is having trouble right now. Please try again in a moment.") from e

    results = _search_results(result.reply.product_ids, result.reply.results_title)
    if result.blocked:
        pass  # a refused message is neither saved nor remembered
    elif user:
        _save_chat(user.id, question, result.reply.reply, results)
    else:
        if len(guest_memory) >= MAX_GUESTS:
            guest_memory.pop(next(iter(guest_memory)))
        guest_memory[guest_key] = result.messages[-GUEST_MESSAGES:]
    return ChatResponse(reply=result.reply.reply, results=results, quick_replies=result.reply.quick_replies, tools_used=result.tools_used)


def _history(user: User) -> list[ChatTurn]:
    return [ChatTurn(role=r["role"], content=r["content"]) for r in _saved_chat(user.id, 30) if r["role"] in ("user", "assistant")]


@app.post("/api/chat/resume", response_model=ChatHistory)
def resume_chat(user: User = Depends(auth.current_user)):
    """A logged-in customer opens the chat: bring their earlier conversation back, like picking it up where they
    left off. If they bought something a few days ago and haven't been asked about it, the chatbot opens with
    "How has it worked out for you?" (once per purchase). That question is saved as the chatbot's message, so when
    the customer answers, the agent can see it in the conversation and file the answer as feedback."""
    due = memory.follow_up_due(user.id, user.first_name)
    if due:
        with auth.db() as conn:
            conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'assistant', ?)", (user.id, due.question))
        memory.mark_asked(due.order_item_id)
    return ChatHistory(messages=_history(user), follow_up=due)


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(user: User = Depends(auth.current_user)):
    """A logged-in customer's recent conversation, so the chat panel can show it again after a refresh."""
    return ChatHistory(messages=_history(user))


IDLE_LIMIT = 4  # offers per person every 15 minutes
IDLE_PROMPT = "(The customer has been quiet for over a minute. This is not something they typed.)"


@app.post("/api/chat/idle", response_model=ChatResponse)
async def chat_idle(body: IdleRequest, request: Request, user: User | None = Depends(auth.optional_user)):
    """The chat panel has been quiet for a minute: Handsome Dan offers a round of Yale trivia, in his own words, to
    keep the customer company and keep them shopping. The website only calls this once per quiet spell. A logged-in
    customer's offer is saved into their chat so it is still there if they come back."""
    ip = request.client.host if request.client else "unknown"
    if auth.throttle(f"idle:{f'user:{user.id}' if user else f'ip:{ip}'}", IDLE_LIMIT):
        raise HTTPException(429, "Enough offers for now.")
    guest_key = f"{ip}:{body.session_id or ''}"
    history = _as_messages(_saved_chat(user.id, HISTORY_MESSAGES)) if user else guest_memory.get(guest_key, [])
    try:
        deps = AgentDeps(user=user, page=pages.build_context(body.page), visitor_key=f"user:{user.id}" if user else guest_key, idle=True)
        result = await agent.chat(IDLE_PROMPT, history, deps)
    except agent.NotConfigured as e:
        raise HTTPException(503, "The shop assistant isn't set up yet (it needs an API key).") from e
    except Exception as e:
        log.exception("idle offer failed")
        raise HTTPException(502, "Handsome Dan is having trouble right now.") from e
    reply = result.reply
    if not result.blocked:
        if user:
            with auth.db() as conn:
                conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'assistant', ?)", (user.id, reply.reply))
        else:
            guest_memory[guest_key] = result.messages[-GUEST_MESSAGES:]
    return ChatResponse(reply=reply.reply, quick_replies=reply.quick_replies or ["Yes, let's play!", "Not now"], tools_used=[])
