"""Structured types (Pydantic models) used across the shop.

Pydantic checks every one of these when data is created, so a malformed product, chat message or
agent answer is caught at the door instead of causing a strange bug later. They fall into four groups:

  1. what the shop sells (Product ...)
  2. who is logged in (User)
  3. what the website and the API say to each other about chat (ChatRequest, ChatResponse ...)
  4. what the agent takes in, gives back, and what its tools return (AgentDeps, AgentReply, SizeCheck ...)
"""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field


# ---------- 1. the shop ----------
class SizeStock(BaseModel):
    size: str
    quantity: int


class Product(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    search_tags: list[str]
    price: float
    image_url: str
    sizes: list[SizeStock]
    total_stock: int


class SimilarProduct(Product):
    reason: str  # why we suggest it, shown on the card


# ---------- 2. customers ----------
class User(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


# ---------- 3. chat, between the website and the API ----------
class PageState(BaseModel):
    """What the website says about the page the customer is looking at. The browser sends it with every chat
    message, and it is never trusted: the server checks it against the database (see pages.py) before the
    chatbot sees anything."""

    path: str = Field(max_length=200, description="the page's address, like /products/basic-hoodie-big-yale")
    selected_size: str | None = Field(default=None, max_length=10, description="the size chosen on a product page, if any")
    shown_product_ids: list[str] = Field(default_factory=list, max_length=8, description="the product cards currently on the page from the chatbot")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, max_length=100, description="a random id from the browser, used to remember a guest's conversation")
    page: PageState | None = None


class ProductResult(BaseModel):
    """One product card to show on the page. This is the contract between the API and the website:
    every field is filled in from the database (never from the AI's words), and `product_id` is the
    key the website uses to open that product's full page at /products/{product_id}."""

    product_id: str
    name: str
    garment_type: str
    price: float
    price_text: str  # the price ready to display, like "$68.00"
    image_url: str  # where to load the photo
    short_info: str  # a one-line description
    colors: list[str]
    in_stock: bool  # false if every size is sold out


class SearchResults(BaseModel):
    """The matching products the chatbot wants shown on the page the customer is looking at."""

    title: str  # a short heading, like "Gray crewnecks in size L"
    items: list[ProductResult]


class ChatResponse(BaseModel):
    reply: str  # what the chatbot says in the chat panel
    results: SearchResults | None = None  # product cards for the page; null when there is nothing to show
    quick_replies: list[str] = []  # buttons shown under the reply, like A / B / C / D for a trivia question
    tools_used: list[str] = []


class IdleRequest(BaseModel):
    """The chat panel has sat quiet for a minute: the website asks the chatbot to offer something to do."""

    session_id: str | None = Field(default=None, max_length=100)
    page: PageState | None = None


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class FollowUp(BaseModel):
    """A past purchase the chatbot should ask about ("How did it work out?")."""

    order_item_id: int
    product_id: str
    product_name: str
    size: str
    question: str


class ChatHistory(BaseModel):
    messages: list[ChatTurn]
    follow_up: FollowUp | None = None  # set when the chatbot just asked about a past purchase


# ---------- 4. the agent ----------
MAX_ON_PAGE = 8  # the most product cards the chatbot can put on the page at once

PageKind = Literal["home", "products", "product", "about", "gift_certificates", "login", "create_account", "account", "forgot_password", "reset_password", "other"]


class PageContext(BaseModel):
    """The page the customer is on, after the server has checked it. Unlike PageState, everything here is safe to rely on."""

    kind: PageKind
    path: str
    product_id: str | None = None  # only set on a product page, and only if that product exists
    selected_size: str | None = None
    shown_product_ids: list[str] = []  # only real products


@dataclass
class AgentDeps:
    """What every tool can see while the agent works on one message: who is asking (if anyone), which page
    they are on, and a past purchase the chatbot has just asked them about. Tools read the customer's id from
    here, never from anything the AI types, so the AI can't ask for someone else's data."""

    user: User | None = None
    page: PageContext | None = None
    awaiting_feedback: FollowUp | None = None
    visitor_key: str = "anonymous"  # who is chatting, for the trivia score and for counting who reported a mistake (a customer id, or a guest's visit)
    idle: bool = False  # True when the customer has been quiet for a minute and the shop wants an offer made
    lessons: list["Lesson"] = field(default_factory=list)  # what the chatbot has learned that applies to this message


class AgentReply(BaseModel):
    """The agent must answer in exactly this shape. Pydantic rejects anything else and asks it to try again."""

    reply: str = Field(description="What to say to the customer: friendly, plain text, no markdown, usually 1 to 4 sentences.")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_ON_PAGE,
        description=(
            "product_id of every product to show as a card on the customer's page: the best matches from your search, "
            f"best first (at most {MAX_ON_PAGE}), copied exactly from tool results. Empty if there is nothing to show."
        ),
    )
    results_title: str | None = Field(
        default=None,
        max_length=60,
        description="A short heading for the cards on the page, like 'Gray crewnecks in size L'. Only when product_ids is not empty.",
    )
    quick_replies: list[str] = Field(
        default_factory=list,
        max_length=4,
        description="Up to 4 short button labels for the customer's likely next answer, like ['A', 'B', 'C', 'D'] for a trivia question or ['Yes, let's play!', 'Not now'] for an offer. Empty when no buttons are needed.",
    )


# ---------- what the tools hand back to the agent ----------
# These are the facts the agent is allowed to quote. Every number in them (price, quantity) comes
# straight from the database, and agent.py rejects any answer that states a price or a count that
# isn't in them.
class StockLine(BaseModel):
    """How many of one size are in stock, with a plain label so the agent describes it the same way every time."""

    size: str
    quantity: int
    status: Literal["in_stock", "low_stock", "sold_out"]  # low_stock means 5 or fewer left


class ProductSummary(BaseModel):
    """One product in a list (search results, suggestions): enough to answer most questions without a second lookup."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    price_text: str  # the price written the way to say it, like "$68.00"
    colors: list[str]
    tags: list[str]  # extra words that describe the item (colleges, sports, themes)
    stock_by_size: list[StockLine]
    total_stock: int
    reason: str | None = None  # why it was suggested, when it is a suggestion


class ProductDetails(BaseModel):
    """Everything known about one product."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    price_text: str
    colors: list[str]
    tags: list[str]
    stock_by_size: list[StockLine]
    low_stock_sizes: list[str]
    sold_out_sizes: list[str]
    total_stock: int


class SizeOption(BaseModel):
    size: str
    quantity: int


class SizeCheck(BaseModel):
    """The answer to "do you have this in size X?", including the two nearest alternatives."""

    product_id: str
    product_name: str
    requested_size: str
    status: Literal["in_stock", "low_stock", "sold_out", "not_made", "unrecognized_size"]
    quantity: int
    next_size_up: SizeOption | None = None
    next_size_down: SizeOption | None = None
    message: str


class StyleCount(BaseModel):
    garment_type: str
    products: int


class CustomerInfo(BaseModel):
    """What the chatbot is allowed to know about the person it's talking to, and only about them: their own name
    and email. Deliberately no phone number, address, payment details or password data (none of that is given to it)."""

    logged_in: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


class PurchaseInfo(BaseModel):
    """One thing a logged-in customer bought. Product facts and when, nothing about payment."""

    product_id: str
    name: str
    garment_type: str
    colors: list[str]
    size: str
    quantity: int
    purchased_on: str  # a date, like 2026-09-12
    feedback_status: Literal["not_asked", "asked", "given"]  # whether the customer has been asked how it worked out, and answered


class PurchaseHistory(BaseModel):
    logged_in: bool
    purchases: list[PurchaseInfo]  # newest first
    note: str


class FeedbackSaved(BaseModel):
    saved: bool
    product_name: str | None = None
    message: str


class PageInfo(BaseModel):
    """What the chatbot can look up about the page the customer is looking at."""

    kind: PageKind
    description: str  # what this page is, in words
    product: ProductDetails | None = None  # on a product page: that product, with live price and stock
    selected_size_check: SizeCheck | None = None  # on a product page with a size chosen: whether that size is available
    cards_on_page: list[ProductSummary] = []  # product cards the chatbot has put on the page


class AccountHelp(BaseModel):
    topic: str
    steps: list[str]
    page: str | None = None  # where on the website to do it


# ---------- gift certificates ----------
class GiftCardOrder(BaseModel):
    """Someone buying a digital gift certificate for a student (or anyone). No payment details are collected."""

    amount: int = Field(ge=10, le=500, description="whole US dollars")
    purchaser_name: str = Field(min_length=1, max_length=50)
    purchaser_email: str = Field(max_length=254)
    recipient_name: str = Field(min_length=1, max_length=50)
    recipient_email: str = Field(max_length=254)
    message: str = Field(default="", max_length=300)


class GiftCardPurchased(BaseModel):
    code: str  # shown once, here, and emailed to the recipient
    amount: int
    recipient_name: str
    recipient_email: str
    payment_note: str


class GiftCodeCheck(BaseModel):
    code: str = Field(max_length=40)


class GiftCardStatus(BaseModel):
    valid: bool
    last4: str | None = None
    balance: float | None = None  # dollars left on the card
    discount_percent: int


class CheckoutItem(BaseModel):
    product_id: str = Field(max_length=100)
    size: str = Field(max_length=10)
    quantity: int = Field(ge=1, le=10)


class GiftCheckout(BaseModel):
    code: str = Field(max_length=40)
    items: list[CheckoutItem] = Field(min_length=1, max_length=30)


class QuoteLine(BaseModel):
    product_id: str
    name: str
    size: str
    quantity: int
    unit_price: float
    line_total: float


class GiftQuote(BaseModel):
    """What the order would cost when paid with a gift card: 10% off, worked out by the server from real prices."""

    lines: list[QuoteLine]
    subtotal: float
    discount_percent: int
    discount: float
    total: float
    balance: float
    enough: bool  # does the card cover the total?


class GiftReceipt(GiftQuote):
    order_id: int
    balance_remaining: float


# ---------- trivia ----------
class TriviaOption(BaseModel):
    letter: str
    text: str


class TriviaQuestion(BaseModel):
    """A multiple-choice Yale question. The agent must read it out exactly as written and never invent its own."""

    number: int
    of: int
    question: str
    options: list[TriviaOption]
    how_to_answer: str


class TriviaResult(BaseModel):
    valid: bool  # false if the answer couldn't be understood or there is no question waiting
    correct: bool | None = None
    correct_letter: str | None = None
    correct_text: str | None = None
    fun_fact: str | None = None
    score: int = 0
    answered: int = 0
    round_over: bool = False
    shop_search: str | None = None  # a search word to show related gear afterwards
    message: str


# ---------- learning from mistakes ----------
class Lesson(BaseModel):
    """Something the chatbot learned from a customer's correction, in a fixed, checked shape (never free-form instructions)."""

    id: int
    customer_term: str  # what customers say, like "sleeveless"
    not_these: list[str]  # garment types that are wrong for it
    try_instead: list[str]  # the closest garment types we really carry
    note: str
    status: Literal["pending", "active", "disabled"]
    reports: int  # how many different customers have reported it


class LessonSaved(BaseModel):
    saved: bool
    status: str | None = None
    message: str
