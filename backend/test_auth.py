"""Tests for accounts. They run on a throwaway COPY of the database, so real data is never touched.

    .venv/bin/pytest -q
"""

import os
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path

# Point the app at a temporary copy of the database and a temporary email outbox BEFORE importing it.
_tmp = Path(tempfile.mkdtemp())
shutil.copy(Path(__file__).resolve().parent.parent / "data" / "campus_customs.db", _tmp / "pristine.db")
os.environ["CAMPUS_DB"] = str(_tmp / "test.db")
os.environ["CC_OUTBOX"] = str(_tmp / "outbox")
os.environ["AUDIT_TRAIL"] = str(_tmp / "audit_trail.json")
os.environ.pop("SMTP_HOST", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
import main  # noqa: E402
import security  # noqa: E402

GOOD = "Blue-Bulldog-47!"
NEW = {"first_name": "Ana", "last_name": "Lopez", "email": "Ana.Lopez@Example.com", "password": GOOD, "confirm_password": GOOD}


@pytest.fixture()
def client():
    shutil.copy(_tmp / "pristine.db", _tmp / "test.db")  # every test starts from a fresh copy
    auth.reset_limits()
    shutil.rmtree(_tmp / "outbox", ignore_errors=True)
    with TestClient(main.app) as c:
        yield c


def rows(sql, *args):
    conn = sqlite3.connect(_tmp / "test.db")
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def outbox_text():
    files = sorted((_tmp / "outbox").glob("*.txt")) if (_tmp / "outbox").exists() else []
    return files[-1].read_text() if files else None


def test_register_saves_a_row_in_users_and_logs_you_in(client):
    r = client.post("/api/auth/register", json=NEW)
    assert r.status_code == 201
    assert r.json()["first_name"] == "Ana" and r.json()["email"] == "ana.lopez@example.com"
    assert "httponly" in r.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").json()["last_name"] == "Lopez"
    (row,) = rows("SELECT * FROM users WHERE email = 'ana.lopez@example.com'")
    assert (row["name"], row["first_name"], row["last_name"]) == ("Ana Lopez", "Ana", "Lopez")


def test_password_is_never_stored_only_a_salted_hash(client):
    client.post("/api/auth/register", json=NEW)
    (row,) = rows("SELECT password_hash FROM users WHERE email = 'ana.lopez@example.com'")
    scheme, rounds, salt, digest = row["password_hash"].split("$")
    assert scheme == "pbkdf2_sha256" and int(rounds) >= 600_000 and len(salt) == 32 and len(digest) == 64
    assert GOOD.encode() not in (_tmp / "test.db").read_bytes()  # not anywhere in the database file


def test_same_password_gets_a_different_hash_for_each_person(client):
    client.post("/api/auth/register", json=NEW)
    client.post("/api/auth/register", json={**NEW, "first_name": "Ben", "email": "ben@example.com"})
    a, b = rows("SELECT password_hash FROM users WHERE email IN ('ana.lopez@example.com','ben@example.com') ORDER BY id")
    assert a["password_hash"] != b["password_hash"]


def test_passwords_must_match(client):
    r = client.post("/api/auth/register", json={**NEW, "confirm_password": GOOD + "x"})
    assert r.status_code == 422 and "match" in r.json()["detail"]["message"]
    assert not rows("SELECT 1 FROM users WHERE email = 'ana.lopez@example.com'")


@pytest.mark.parametrize(
    "password, rule",
    [
        ("Sh0rt!a", "length"),
        ("NOLOWER-1234!", "lower"),
        ("noupper-1234!", "upper"),
        ("No-Digits-Here!", "digit"),
        ("NoSymbols1234Ab", "special"),
        ("My-Password-123!", "not_common"),
        ("Ana-Lopez-2026!", "not_personal"),
        ("A" * 70 + "a1!", "length"),
    ],
)
def test_weak_passwords_are_refused(client, password, rule):
    r = client.post("/api/auth/register", json={**NEW, "password": password, "confirm_password": password})
    assert r.status_code == 422
    assert rule in r.json()["detail"]["rules"]


def test_email_is_not_case_sensitive_and_cannot_be_reused(client):
    client.post("/api/auth/register", json=NEW)
    r = client.post("/api/auth/register", json={**NEW, "email": "ANA.LOPEZ@EXAMPLE.COM"})
    assert r.status_code == 409


@pytest.mark.parametrize("bad", [{"email": "not-an-email"}, {"first_name": "<script>"}, {"last_name": ""}, {"first_name": "R2D2"}])
def test_bad_names_and_emails_are_refused(client, bad):
    assert client.post("/api/auth/register", json={**NEW, **bad}).status_code == 422


def test_login_logout_and_me(client):
    client.post("/api/auth/register", json=NEW)
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "ANA.LOPEZ@example.com ", "password": GOOD}).status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_wrong_password_and_unknown_email_look_identical(client):
    client.post("/api/auth/register", json=NEW)
    client.post("/api/auth/logout")
    wrong = client.post("/api/auth/login", json={"email": NEW["email"], "password": "Wrong-Pass-1!"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Wrong-Pass-1!"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_too_many_wrong_guesses_locks_the_account_for_a_while(client):
    client.post("/api/auth/register", json=NEW)
    client.post("/api/auth/logout")
    for _ in range(auth.MAX_BY_EMAIL):
        assert client.post("/api/auth/login", json={"email": NEW["email"], "password": "Wrong-Pass-1!"}).status_code == 401
    locked = client.post("/api/auth/login", json={"email": NEW["email"], "password": GOOD})  # even the right one
    assert locked.status_code == 429


def test_forgot_password_gives_the_same_answer_for_known_and_unknown_emails(client):
    client.post("/api/auth/register", json=NEW)
    known = client.post("/api/auth/forgot-password", json={"email": NEW["email"]})
    assert known.status_code == 200 and "reset-password?token=" in outbox_text()
    shutil.rmtree(_tmp / "outbox")
    unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert unknown.json() == known.json()
    assert outbox_text() is None  # and no email was written for a stranger


def test_full_password_reset(client):
    client.post("/api/auth/register", json=NEW)
    client.post("/api/auth/forgot-password", json={"email": NEW["email"]})
    token = re.search(r"token=([\w-]+)", outbox_text()).group(1)
    assert token not in (_tmp / "test.db").read_bytes().decode("latin-1")  # only a fingerprint is stored

    other = "Green-Tower-88?"
    assert client.post("/api/auth/reset-password", json={"token": token, "password": other, "confirm_password": "nope"}).status_code == 422
    assert client.post("/api/auth/reset-password", json={"token": token, "password": "weak", "confirm_password": "weak"}).status_code == 422
    assert client.post("/api/auth/reset-password", json={"token": token, "password": other, "confirm_password": other}).status_code == 200

    assert client.get("/api/auth/me").status_code == 401  # old sessions were ended
    assert client.post("/api/auth/login", json={"email": NEW["email"], "password": GOOD}).status_code == 401
    assert client.post("/api/auth/login", json={"email": NEW["email"], "password": other}).status_code == 200
    assert client.post("/api/auth/reset-password", json={"token": token, "password": GOOD, "confirm_password": GOOD}).status_code == 400  # link works once


def test_expired_reset_link_is_refused(client):
    client.post("/api/auth/register", json=NEW)
    client.post("/api/auth/forgot-password", json={"email": NEW["email"]})
    token = re.search(r"token=([\w-]+)", outbox_text()).group(1)
    conn = sqlite3.connect(_tmp / "test.db")
    conn.execute("UPDATE password_resets SET expires_at = '2000-01-01 00:00:00'")
    conn.commit()
    conn.close()
    assert client.post("/api/auth/reset-password", json={"token": token, "password": GOOD, "confirm_password": GOOD}).status_code == 400


def test_made_up_reset_token_is_refused(client):
    assert client.post("/api/auth/reset-password", json={"token": "x" * 40, "password": GOOD, "confirm_password": GOOD}).status_code == 400


def test_customers_with_the_old_hash_format_can_log_in_and_get_upgraded(client):
    import hashlib

    salt = "abcdef0123456789"  # an old-style hash: scheme$salt$hash, no round count written down
    old_hash = f"pbkdf2_sha256${salt}${hashlib.pbkdf2_hmac('sha256', b'Old-Test-Pass-1!', salt.encode(), 100_000).hex()}"
    conn = sqlite3.connect(_tmp / "test.db")
    conn.execute("UPDATE users SET password_hash = ? WHERE id = 1", (old_hash,))
    conn.commit()
    conn.close()
    (user,) = rows("SELECT email FROM users WHERE id = 1")
    assert client.post("/api/auth/login", json={"email": user["email"], "password": "Wrong-Pass-1!"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": user["email"], "password": "Old-Test-Pass-1!"}).status_code == 200
    (row,) = rows("SELECT password_hash FROM users WHERE id = 1")
    assert row["password_hash"].startswith("pbkdf2_sha256$600000$")  # upgraded to the new format
    assert client.post("/api/auth/login", json={"email": user["email"], "password": "Old-Test-Pass-1!"}).status_code == 200


def test_existing_customers_with_the_old_hash_format_can_reset_their_password(client):
    (old,) = rows("SELECT email, password_hash FROM users ORDER BY id LIMIT 1")
    client.post("/api/auth/forgot-password", json={"email": old["email"]})
    token = re.search(r"token=([\w-]+)", outbox_text()).group(1)
    new = "Maple-Street-52!"
    assert client.post("/api/auth/reset-password", json={"token": token, "password": new, "confirm_password": new}).status_code == 200
    assert client.post("/api/auth/login", json={"email": old["email"], "password": new}).status_code == 200
    assert security.verify_password(new, rows("SELECT password_hash FROM users WHERE email = ?", old["email"])[0]["password_hash"])


def test_shop_still_works(client):
    assert len(client.get("/api/products").json()) == 102
    assert client.get("/api/health").json()["status"] == "ok"


def test_changing_your_password_needs_you_to_be_logged_in(client):
    r = client.post("/api/auth/change-password", json={"current_password": GOOD, "password": "Green-Tower-88?", "confirm_password": "Green-Tower-88?"})
    assert r.status_code == 401


def test_change_password(client):
    client.post("/api/auth/register", json=NEW)
    laptop = client
    with TestClient(main.app) as phone:  # a second device logged in as the same person
        assert phone.post("/api/auth/login", json={"email": NEW["email"], "password": GOOD}).status_code == 200
        new = "Green-Tower-88?"
        body = {"current_password": GOOD, "password": new, "confirm_password": new}

        assert laptop.post("/api/auth/change-password", json={**body, "current_password": "Not-My-Pass-1!"}).status_code == 400  # wrong current
        assert laptop.post("/api/auth/change-password", json={**body, "confirm_password": "nope"}).status_code == 422  # mismatch
        assert laptop.post("/api/auth/change-password", json={**body, "password": "weak", "confirm_password": "weak"}).status_code == 422
        assert laptop.post("/api/auth/change-password", json={"current_password": GOOD, "password": GOOD, "confirm_password": GOOD}).status_code == 422  # not new

        assert laptop.post("/api/auth/change-password", json=body).status_code == 200
        assert "password was changed" in outbox_text()  # a heads-up email, in case it wasn't them
        assert laptop.get("/api/auth/me").status_code == 200  # this device stays logged in
        assert phone.get("/api/auth/me").status_code == 401  # the other one is logged out

    laptop.post("/api/auth/logout")
    assert laptop.post("/api/auth/login", json={"email": NEW["email"], "password": GOOD}).status_code == 401
    assert laptop.post("/api/auth/login", json={"email": NEW["email"], "password": new}).status_code == 200
    (row,) = rows("SELECT password_hash FROM users WHERE email = 'ana.lopez@example.com'")
    assert row["password_hash"].startswith("pbkdf2_sha256$600000$") and new not in row["password_hash"]


def test_guessing_the_current_password_gets_locked_out(client):
    client.post("/api/auth/register", json=NEW)
    body = {"current_password": "Not-My-Pass-1!", "password": "Green-Tower-88?", "confirm_password": "Green-Tower-88?"}
    for _ in range(auth.MAX_BY_EMAIL):
        assert client.post("/api/auth/change-password", json=body).status_code == 400
    assert client.post("/api/auth/change-password", json={**body, "current_password": GOOD}).status_code == 429
