"""Accounts: create account, log in, log out, "who am I", forgot password, reset password.

New accounts are saved as rows in the `users` table. Passwords are never saved: only a salted, slow
hash of each one (see security.py). A logged-in browser holds a random session code in an HttpOnly
cookie (JavaScript can't read it); the database keeps only a fingerprint of that code.
"""

import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

import security
from config import COOKIE_SECURE, DB_PATH, FRONTEND_URL, RESET_MINUTES, SESSION_COOKIE, SESSION_DAYS
from emailer import send_email
from models import User

router = APIRouter(prefix="/api/auth", tags=["accounts"])

EMAIL_PATTERN = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]{2,}$")
BAD_LOGIN = "That email and password don't match. Please try again."
FORGOT_REPLY = f"If there's an account for that email, we've sent a password reset link. It works for {RESET_MINUTES} minutes."


# ---------- database ----------
@contextmanager
def db():
    """A connection that can write. Commits if the block finishes, undoes everything if it fails."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_tables() -> None:
    """The two extra tables accounts need. Safe to run every time the API starts."""
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )


def _stamp(minutes: float = 0) -> str:
    """UTC time as text, in the same shape SQLite's datetime('now') uses, so they sort correctly."""
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")


# ---------- guessing limits ----------
# Remember recent failed attempts (in memory, so a restart clears them) and stop guessing.
WINDOW_SECONDS = 15 * 60
MAX_BY_EMAIL = 5
MAX_BY_IP = 25
_failures: dict[str, list[float]] = {}


def _recent(key: str) -> list[float]:
    cutoff = time.time() - WINDOW_SECONDS
    _failures[key] = [t for t in _failures.get(key, []) if t > cutoff]
    return _failures[key]


MAX_RESET_EMAILS = 3  # reset emails per address per window


def _wait_minutes(*checks: tuple[str, int]) -> int:
    """Minutes left before any of these (key, limit) pairs allows another try, or 0 if none is full."""
    wait = 0.0
    for key, limit in checks:
        hits = _recent(key)
        if len(hits) >= limit:
            wait = max(wait, hits[0] + WINDOW_SECONDS - time.time())
    return int(wait // 60) + 1 if wait > 0 else 0


def _count(*keys: str) -> None:
    for key in keys:
        _failures.setdefault(key, []).append(time.time())


def reset_limits() -> None:
    _failures.clear()


# ---------- request shapes ----------
def _clean_name(v: str) -> str:
    v = " ".join(v.split())
    if not v or len(v) > 50 or re.search(r"[<>{}\[\]\\/@;=$|]|\d", v):
        raise ValueError("Please enter a real name (letters only, up to 50 characters).")
    return v


class RegisterBody(BaseModel):
    first_name: str
    last_name: str
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    confirm_password: str = Field(max_length=200)

    @field_validator("first_name", "last_name")
    @classmethod
    def _names(cls, v: str) -> str:
        return _clean_name(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_PATTERN.match(v):
            raise ValueError("Please enter a valid email address.")
        return v


class LoginBody(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class ForgotBody(BaseModel):
    email: str = Field(max_length=254)


class ResetBody(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(max_length=200)
    confirm_password: str = Field(max_length=200)


class ChangePasswordBody(BaseModel):
    current_password: str = Field(max_length=200)
    password: str = Field(max_length=200)
    confirm_password: str = Field(max_length=200)


def _problem(status: int, message: str, rules: list[str] | None = None) -> HTTPException:
    return HTTPException(status, {"message": message, "rules": rules or []})


def _check_new_password(password: str, confirm: str, email: str = "", first: str = "", last: str = "") -> None:
    if password != confirm:
        raise _problem(422, "The two passwords don't match.")
    broken = security.failed_rules(password, email, first, last)
    if broken:
        raise _problem(422, "That password isn't strong enough.", broken)


def _user_from(row: sqlite3.Row) -> User:
    return User(id=row["id"], first_name=row["first_name"] or "", last_name=row["last_name"] or "", email=row["email"])


# ---------- sessions ----------
def _start_session(conn: sqlite3.Connection, response: Response, user_id: int) -> None:
    token = security.new_token()
    conn.execute(
        "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (user_id, security.hash_token(token), _stamp(SESSION_DAYS * 24 * 60)),
    )
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_DAYS * 24 * 3600, httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/"
    )


def current_user(cc_session: str | None = Cookie(default=None)) -> User:
    """Who is logged in, from the session cookie. Used by any route that needs a signed-in customer."""
    if cc_session:
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (_stamp(),))
            row = conn.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
                (security.hash_token(cc_session),),
            ).fetchone()
        if row:
            return _user_from(row)
    raise HTTPException(401, "Please log in.")


def optional_user(cc_session: str | None = Cookie(default=None)) -> User | None:
    """Like current_user, but returns None for a guest instead of an error (the chatbot works for both)."""
    try:
        return current_user(cc_session)
    except HTTPException:
        return None


def throttle(key: str, limit: int) -> int:
    """Count one use of `key`. Returns 0 if it's allowed, or the minutes to wait if `limit` uses
    have already happened in the last 15 minutes."""
    wait = _wait_minutes((key, limit))
    if not wait:
        _count(key)
    return wait


# ---------- routes ----------
@router.post("/register", status_code=201, response_model=User)
def register(body: RegisterBody, response: Response):
    _check_new_password(body.password, body.confirm_password, body.email, body.first_name, body.last_name)
    with db() as conn:
        # the email column ignores capital letters, so "A@x.com" and "a@x.com" count as the same account
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (body.email,)).fetchone():
            raise _problem(409, "There's already an account with that email. Try logging in instead.")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{body.first_name} {body.last_name}", body.email, security.hash_password(body.password), body.first_name, body.last_name),
        )
        _start_session(conn, response, cur.lastrowid)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _user_from(row)


@router.post("/login", response_model=User)
def login(body: LoginBody, request: Request, response: Response):
    email = body.email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    minutes = _wait_minutes((f"email:{email}", MAX_BY_EMAIL), (f"ip:{ip}", MAX_BY_IP))
    if minutes:
        raise _problem(429, f"Too many tries. Please wait about {minutes} minute{'s' if minutes != 1 else ''} and try again, or reset your password.")
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        # always do one full hash check, even for an unknown email, so timing doesn't give it away
        ok = security.verify_password(body.password, row["password_hash"] if row else security.DUMMY_HASH)
        if not (row and ok):
            _count(f"email:{email}", f"ip:{ip}")
            raise _problem(401, BAD_LOGIN)
        _failures.pop(f"email:{email}", None)
        if security.needs_rehash(row["password_hash"]):  # quietly upgrade old hashes
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (security.hash_password(body.password), row["id"]))
        _start_session(conn, response, row["id"])
    return _user_from(row)


@router.post("/logout", status_code=204)
def logout(response: Response, cc_session: str | None = Cookie(default=None)):
    if cc_session:
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (security.hash_token(cc_session),))
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=User)
def me(user: User = Depends(current_user)):
    return user


@router.post("/change-password")
def change_password(body: ChangePasswordBody, cc_session: str | None = Cookie(default=None), user: User = Depends(current_user)):
    """A logged-in customer chooses a new password. They must type their current one first, so someone
    who finds an unlocked laptop can't take over the account."""
    key = f"change:{user.id}"
    minutes = _wait_minutes((key, MAX_BY_EMAIL))
    if minutes:
        raise _problem(429, f"Too many tries. Please wait about {minutes} minute{'s' if minutes != 1 else ''} and try again.")
    with db() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user.id,)).fetchone()
        if not security.verify_password(body.current_password, row["password_hash"]):
            _count(key)
            raise _problem(400, "Your current password isn't right.")
        if body.password == body.current_password:
            raise _problem(422, "Please choose a password that's different from your current one.")
        _check_new_password(body.password, body.confirm_password, user.email, user.first_name, user.last_name)
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (security.hash_password(body.password), user.id))
        # log out every other device, but keep this one signed in
        conn.execute("DELETE FROM sessions WHERE user_id = ? AND token_hash != ?", (user.id, security.hash_token(cc_session or "")))
    _failures.pop(key, None)
    send_email(
        user.email,
        "Your Campus Customs password was changed",
        f"Hi {user.first_name or 'there'},\n\nThe password for your Campus Customs account was just changed. "
        "If that was you, there's nothing more to do.\n\nIf it wasn't you, please reset your password right away at "
        f"{FRONTEND_URL}/forgot-password.\n\nLux et Veritas,\nCampus Customs",
    )
    return {"message": "Your password has been changed. Any other devices were logged out."}


@router.post("/forgot-password")
def forgot_password(body: ForgotBody, request: Request):
    """Emails a reset link to the address on file. The reply is the same whether or not the email is
    registered, so nobody can use this form to find out who has an account."""
    email = body.email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    if _wait_minutes((f"reset:{email}", MAX_RESET_EMAILS), (f"resetip:{ip}", MAX_BY_IP)):
        return {"message": FORGOT_REPLY}  # same reply, but no email: this can't be used to flood an inbox
    _count(f"reset:{email}", f"resetip:{ip}")
    with db() as conn:
        row = conn.execute("SELECT id, first_name FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            token = security.new_token()
            conn.execute("DELETE FROM password_resets WHERE user_id = ?", (row["id"],))  # one live link at a time
            conn.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
                (row["id"], security.hash_token(token), _stamp(RESET_MINUTES)),
            )
            link = f"{FRONTEND_URL}/reset-password?token={token}"
            send_email(
                email,
                "Reset your Campus Customs password",
                f"Hi {row['first_name'] or 'there'},\n\nSomeone asked to reset the password for your Campus Customs account. "
                f"To choose a new one, open this link within {RESET_MINUTES} minutes:\n\n{link}\n\n"
                "If that wasn't you, you can ignore this email and your password will stay the same.\n\nLux et Veritas,\nCampus Customs",
            )
    return {"message": FORGOT_REPLY}


@router.post("/reset-password")
def reset_password(body: ResetBody):
    with db() as conn:
        conn.execute("DELETE FROM password_resets WHERE expires_at <= ?", (_stamp(),))
        reset = conn.execute("SELECT * FROM password_resets WHERE token_hash = ?", (security.hash_token(body.token),)).fetchone()
        if not reset:
            raise _problem(400, "This reset link has expired or was already used. Please ask for a new one.")
        user = conn.execute("SELECT * FROM users WHERE id = ?", (reset["user_id"],)).fetchone()
        _check_new_password(body.password, body.confirm_password, user["email"], user["first_name"] or "", user["last_name"] or "")
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (security.hash_password(body.password), user["id"]))
        conn.execute("DELETE FROM password_resets WHERE user_id = ?", (user["id"],))  # the link works once
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))  # log out everywhere else
    return {"message": "Your password has been changed. Please log in with your new password."}
