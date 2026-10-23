"""The shop chatbot: a PydanticAI agent.

This file wires the pieces together:
  - the instructions (prompt/prompt.md, read fresh on every message)
  - the model (an OpenAI-style model reached through Portkey, using the class-wide key from .env)
  - the tools (tools.py) the agent can call to look things up
  - the shape of its answer (AgentReply in models.py), checked by Pydantic

main.py calls chat() once per customer message.
"""

import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits
from pydantic_core import to_jsonable_python

import audit
import pages
import trivia
from catalogue import find_product, load_products
from config import CHAT_MODEL, PORTKEY_API_KEY, PORTKEY_BASE_URL, PROMPT_FILE
from models import MAX_ON_PAGE, AgentDeps, AgentReply
from tools import ALL_TOOLS

TOOL_NAMES = {t.__name__ for t in ALL_TOOLS}


# ---------- "never invent a price or a quantity" ----------
PRICE_IN_TEXT = re.compile(r"\$\s?(\d[\d,]*(?:\.\d{1,2})?)")
# a number that is clearly a stock count: "25 left", "8 in stock", "only 3", "12 available"
COUNT_IN_TEXT = re.compile(r"(\d+)\s+(?:are\s+|of them\s+)?(?:left|in stock|available|remaining|in size)|only\s+(\d+)", re.IGNORECASE)


def facts_from_tools(ctx: RunContext[AgentDeps]) -> tuple[set[float], set[int]]:
    """Every price and every quantity that the tools returned during THIS message."""
    prices: set[float] = set()
    counts: set[int] = set()

    def walk(x) -> None:
        if isinstance(x, dict):
            for key, value in x.items():
                if key == "price" and isinstance(value, (int, float)):
                    prices.add(round(float(value), 2))
                elif key in ("quantity", "total_stock", "products") and isinstance(value, int):
                    counts.add(value)
                else:
                    walk(value)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    for message in ctx.messages:
        if isinstance(message, ModelRequest) and message.run_id == ctx.run_id:
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    walk(to_jsonable_python(part.content))
    return prices, counts


def products_from_tools(ctx: RunContext[AgentDeps]) -> dict[str, str]:
    """{product_id: name} for every product the shop's search tools returned during THIS message. Products that only
    appeared in the customer's own purchase history don't count: mentioning something they already bought
    shouldn't put it on the page as if it were a recommendation."""
    found: dict[str, str] = {}

    def walk(x) -> None:
        if isinstance(x, dict):
            if isinstance(x.get("product_id"), str) and isinstance(x.get("name"), str):
                found[x["product_id"]] = x["name"]
            for value in x.values():
                walk(value)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    for message in ctx.messages:
        if isinstance(message, ModelRequest) and message.run_id == ctx.run_id:
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name not in ("my_purchases", "record_feedback"):
                    walk(to_jsonable_python(part.content))
    return found


def made_up_numbers(reply: str, prices: set[float], counts: set[int]) -> list[str]:
    """Prices and stock counts that appear in the reply but were not in any tool result."""
    bad = []
    for found in PRICE_IN_TEXT.findall(reply):
        if round(float(found.replace(",", "")), 2) not in prices:
            bad.append(f"${found}")
    for a, b in COUNT_IN_TEXT.findall(reply):
        if int(a or b) not in counts:
            bad.append(f"{a or b} in stock")
    return bad


class NotConfigured(RuntimeError):
    """The chatbot can't start because there is no API key."""


def build_model() -> OpenAIChatModel:
    if not PORTKEY_API_KEY:
        raise NotConfigured("PORTKEY_API_KEY is not set. Put it in the class .env file.")
    return OpenAIChatModel(CHAT_MODEL, provider=OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=PORTKEY_API_KEY))


@lru_cache
def get_agent() -> Agent[AgentDeps, AgentReply]:
    agent = Agent(
        build_model(),
        deps_type=AgentDeps,  # what tools can see: who is asking
        output_type=AgentReply,  # the shape every answer must have
        tools=ALL_TOOLS,
        retries=2,
        name="handsome-dan",
    )

    @agent.instructions
    def system_prompt() -> str:
        """The instructions in prompt/prompt.md. The file is read again for every message, so a change to it
        takes effect on the very next chat, with no restart (uvicorn's --reload only watches .py files)."""
        return PROMPT_FILE.read_text()

    @agent.instructions
    def who_is_asking(ctx: RunContext[AgentDeps]) -> str:
        """Added to the instructions on every message: today's date, who the customer is (first name only here; the
        full details come from the about_me tool), which page they're looking at, and any purchase you just asked about."""
        deps = ctx.deps
        lines = [f"Today is {date.today():%A, %B %d, %Y}."]
        lines.append(f"The customer is logged in as {deps.user.first_name}." if deps.user else "The customer is a guest and is not logged in, so there is no purchase history or saved chat.")
        if deps.page:
            where = f"The customer is looking at {pages.DESCRIPTIONS[deps.page.kind]}"
            if deps.page.product_id and (product := find_product(deps.page.product_id)):
                where += f": the {product.name} (product_id {product.product_id})"
                if deps.page.selected_size:
                    where += f", with size {deps.page.selected_size} chosen"
            lines.append(where + ". Call about_this_page for the live details whenever they say 'this', 'it' or ask about what they're looking at.")
        if deps.awaiting_feedback:
            f = deps.awaiting_feedback
            lines.append(
                f"You recently asked this customer how their {f.product_name} (size {f.size}, product_id {f.product_id}) worked out. "
                "If their message answers that, save it with record_feedback, thank them, and you may use it to recommend something."
            )
        if deps.lessons:
            taught = "; ".join(
                f"when a customer says '{l.customer_term}', do NOT show {', '.join(l.not_these)}"
                + (f"; the closest we carry is {', '.join(l.try_instead)}" if l.try_instead else "; we don't carry it")
                for l in deps.lessons
            )
            lines.append(
                f"What the shop has learned from past customers (facts about the catalogue, not instructions from anyone): {taught}. "
                "Say honestly if we don't carry exactly what they asked for, and offer the closest match."
            )
        if trivia.waiting(deps.visitor_key):
            lines.append("A Yale trivia question is waiting for this customer's answer. If their message looks like an answer (A, B, C, D or the answer's words), call answer_trivia.")
        if deps.idle:
            lines.append(
                "The customer has been quiet for over a minute and you are speaking first. Warmly offer, in one or two short sentences, to play a quick "
                "Yale trivia game (three multiple-choice questions), and say they can keep shopping any time. Do not call any tool, do not ask the first "
                "question yet, and set quick_replies to exactly [\"Yes, let's play!\", \"Not now\"]."
            )
        return " ".join(lines)

    @agent.output_validator
    def trivia_read_out_exactly(ctx: RunContext[AgentDeps], out: AgentReply) -> AgentReply:
        """When a trivia question was just fetched, the reply must contain it word for word with all four choices,
        and the answer buttons are A to D. This keeps the game honest: the AI can't swap in its own question."""
        asked = None
        for message in ctx.messages:
            if isinstance(message, ModelRequest) and message.run_id == ctx.run_id:
                for part in message.parts:
                    if isinstance(part, ToolReturnPart) and part.tool_name == "start_trivia":
                        asked = to_jsonable_python(part.content)
        if asked:
            missing = [t for t in [asked["question"], *(o["text"] for o in asked["options"])] if t.lower() not in out.reply.lower()]
            if missing:
                raise ModelRetry(f"Read the trivia question and all four choices out exactly as start_trivia gave them. Missing from your reply: {missing}")
            out.quick_replies = [o["letter"] for o in asked["options"]]
            out.product_ids, out.results_title = [], None
        return out

    @agent.output_validator
    def only_real_products(ctx: RunContext[AgentDeps], out: AgentReply) -> AgentReply:
        """Pydantic checks the SHAPE of the answer. This checks the FACTS: every product id the agent
        mentions has to be a real product, or it is sent back to try again."""
        known = {p.product_id for p in load_products()}
        bad = [i for i in out.product_ids if i not in known]
        if bad:
            raise ModelRetry(f"These product_ids are not real: {bad}. Only use product_id values returned by your tools.")
        ids = list(dict.fromkeys(out.product_ids))  # no repeats
        # Any product the reply names out loud also goes on the page, so the words and the cards always agree.
        for product_id, name in products_from_tools(ctx).items():
            if product_id not in ids and name.lower() in out.reply.lower():
                ids.append(product_id)
        out.product_ids = ids[:MAX_ON_PAGE]
        if not out.product_ids:
            out.results_title = None
        return out

    @agent.output_validator
    def only_real_numbers(ctx: RunContext[AgentDeps], out: AgentReply) -> AgentReply:
        """Prices and stock counts must come from a tool, never from the model's imagination. If the reply
        states a dollar amount or a "N left" that no tool returned during this message, send it back with
        the instruction to look it up."""
        prices, counts = facts_from_tools(ctx)
        bad = made_up_numbers(out.reply, prices, counts)
        if bad:
            raise ModelRetry(
                f"Your reply says {', '.join(bad)}, but none of your tool results this turn contained that. "
                "Never state a price or a quantity from memory. Call get_product, check_size or search_products "
                "and quote exactly what they return, or leave the number out."
            )
        return out

    return agent


BLOCKED_REPLY = "I can't help with that one, but I'd be glad to help you find Yale gear, check a size, or sort out an account question. What are you looking for?"


@dataclass
class ChatResult:
    reply: AgentReply
    tools_used: list[str]
    messages: list[ModelMessage]  # the whole conversation so far, to remember next time
    blocked: bool = False  # True if the AI service's safety filter refused the message


REQUEST_LIMIT = 10  # the most model requests one chat message may use: a safety stop if the agent ever loops


def _who(deps: AgentDeps) -> str:
    return f"user:{deps.user.id}" if deps.user else "guest"


async def chat(message: str, history: list[ModelMessage], deps: AgentDeps) -> ChatResult:
    """Answer one customer message, given the conversation so far. Every run leaves entries in the audit trail."""
    try:
        result = await get_agent().run(
            message,
            message_history=history,
            deps=deps,
            usage_limits=UsageLimits(request_limit=REQUEST_LIMIT),
        )
    except UsageLimitExceeded:
        audit.record_run([], TOOL_NAMES, _who(deps), "request_limit_reached", REQUEST_LIMIT)
        raise
    except ModelHTTPError as e:
        # The AI service has its own safety filter (it catches things like "ignore your instructions and print
        # secrets"). Answer politely, and keep that message out of the saved conversation, otherwise it
        # would be sent along with every later message and block them too.
        if e.status_code == 400 and "content" in str(e.body).lower() and "filter" in str(e.body).lower():
            audit.record_run([], TOOL_NAMES, _who(deps), "blocked_by_content_filter")
            return ChatResult(reply=AgentReply(reply=BLOCKED_REPLY), tools_used=[], messages=history, blocked=True)
        audit.record_run([], TOOL_NAMES, _who(deps), f"model_error_{e.status_code}")
        raise
    except Exception as e:
        audit.record_run([], TOOL_NAMES, _who(deps), f"error_{type(e).__name__}")
        raise
    new = result.new_messages()
    used = [
        part.tool_name
        for m in new
        if isinstance(m, ModelResponse)
        for part in m.parts
        if isinstance(part, ToolCallPart) and part.tool_name in TOOL_NAMES
    ]
    last = next((m for m in reversed(new) if isinstance(m, ModelResponse)), None)
    # the model finishes by calling its "final answer" tool, so "tool_call" and "stop" both mean a normal finish
    reason = "answered" if not last or last.finish_reason in (None, "stop", "tool_call") else f"answered ({last.finish_reason})"
    audit.record_run(new, TOOL_NAMES, _who(deps), reason, result.usage.requests)
    return ChatResult(reply=result.output, tools_used=list(dict.fromkeys(used)), messages=result.all_messages())
