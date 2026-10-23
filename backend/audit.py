"""The audit trail: a permanent, append-only record of what the chatbot's agent loop did.

Every chat message runs the agent in a loop: the model may call tools, get results, maybe be sent back to fix an
answer, and then gives its final answer. After each run this file adds one entry per step to `output/audit_trail.json`:

    tool_call   time, tool name, short arguments, short result
    retry       time, why the shop sent the model back to try again (the answer failed a check)
    stop        time, stop reason, tools used, how many model requests the loop made

The file is one valid JSON list. New entries are written onto the END of it (the closing bracket is overwritten by the
new entry plus a fresh closing bracket), so nothing already in the file is ever rewritten, and a restart never wipes it.
It is safe to read at any time.

What is NOT in it, on purpose: the customer's messages, their name or email, any password, and the chatbot's replies.
Arguments and results are shortened to about 160 characters, email addresses and long digit strings are masked, and
tools that return personal details (about_me, my_purchases) are reduced to a count or a yes/no. Customers appear only
as "guest" or "user:<id>".
"""

import fcntl
import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timezone

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart
from pydantic_core import to_jsonable_python

from config import AUDIT_FILE

log = logging.getLogger("campus-customs.audit")
_lock = threading.Lock()
SHORT = 160
EMAIL = re.compile(r"[^\s@\"']+@[^\s@\"']+\.[a-z]{2,}", re.IGNORECASE)
LONG_NUMBER = re.compile(r"\d{9,}")


def _clean(text: str) -> str:
    text = EMAIL.sub("[email]", text)
    text = LONG_NUMBER.sub("[number]", text)
    text = " ".join(text.split())
    return text if len(text) <= SHORT else text[: SHORT - 1] + "…"


def short(value) -> str:
    """Any value as a short, masked string."""
    try:
        text = value if isinstance(value, str) else json.dumps(to_jsonable_python(value), ensure_ascii=False, default=str)
    except Exception:
        text = str(value)
    return _clean(text)


def _summarize_result(tool: str, content) -> str:
    """What a tool returned, in a few words. Tools that handle personal details are reduced to counts."""
    data = to_jsonable_python(content)
    if tool == "about_me":
        return short({"logged_in": bool(isinstance(data, dict) and data.get("logged_in"))})
    if tool == "my_purchases":
        n = len(data.get("purchases", [])) if isinstance(data, dict) else 0
        return f"{n} past purchase(s)"
    if isinstance(data, list) and data and isinstance(data[0], dict) and "name" in data[0]:
        names = ", ".join(str(d.get("name")) for d in data[:3])
        return _clean(f"{len(data)} product(s): {names}" + (", ..." if len(data) > 3 else ""))
    if isinstance(data, list):
        return _clean(f"{len(data)} item(s)")
    return short(data)


def _summarize_args(args) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            return _clean(args)
    return short(args or {})


def _now(ts: datetime | None = None) -> str:
    return (ts or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def entries_for_run(messages: list[ModelMessage], tool_names: set[str], who: str, stop_reason: str, run_id: str, requests: int | None = None) -> list[dict]:
    """Turns one run's messages into audit entries, in order."""
    out: list[dict] = []
    calls: dict[str, tuple[str, str]] = {}  # tool_call_id -> (tool, short args)
    used: list[str] = []
    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart) and part.tool_name in tool_names:
                    calls[part.tool_call_id] = (part.tool_name, _summarize_args(part.args))
        elif isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name in tool_names:
                    tool, args = calls.get(part.tool_call_id, (part.tool_name, ""))
                    used.append(tool)
                    out.append({"time": _now(part.timestamp), "run_id": run_id, "who": who, "event": "tool_call", "tool": tool, "args": args, "result": _summarize_result(tool, part.content)})
                elif isinstance(part, RetryPromptPart):
                    reason = part.content if isinstance(part.content, str) else short(part.content)
                    out.append({"time": _now(part.timestamp), "run_id": run_id, "who": who, "event": "retry", "tool": part.tool_name or "answer check", "result": _clean(reason)})
    out.append({"time": _now(), "run_id": run_id, "who": who, "event": "stop", "stop_reason": stop_reason, "tools_used": list(dict.fromkeys(used)), "model_requests": requests})
    return out


def append(entries: list[dict]) -> None:
    """Adds entries to the end of the audit file. Never rewrites, truncates or deletes what is already there."""
    if not entries:
        return
    body = ",\n".join("  " + json.dumps(e, ensure_ascii=False) for e in entries).encode()
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        fd = os.open(AUDIT_FILE, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)  # also safe if two servers ever run at once
            size = os.fstat(fd).st_size
            if size == 0:
                os.write(fd, b"[\n" + body + b"\n]\n")
                return
            tail = os.pread(fd, min(size, 16), size - min(size, 16))
            stripped = tail.rstrip()
            if not stripped.endswith(b"]"):
                raise ValueError("audit_trail.json does not end with ']'; leaving it untouched")
            kept = stripped[:-1].rstrip()  # what comes before the closing bracket
            position = size - len(tail) + len(kept)  # we start writing right after the last entry
            comma = b"\n" if kept.endswith(b"[") else b",\n"
            os.pwrite(fd, comma + body + b"\n]\n", position)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


def record_run(messages: list[ModelMessage], tool_names: set[str], who: str, stop_reason: str, requests: int | None = None) -> None:
    """Called after every agent run. Auditing must never break the chat, so any problem is only logged."""
    try:
        append(entries_for_run(messages, tool_names, who, stop_reason, uuid.uuid4().hex[:12], requests))
    except Exception:
        log.exception("could not write the audit trail")
