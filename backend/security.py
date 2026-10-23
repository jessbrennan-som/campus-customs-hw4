"""Password rules, password hashing and secret tokens. No web code in here, so it is easy to test."""

import base64
import hashlib
import hmac
import re
import secrets

# ---------- hashing ----------
# PBKDF2-HMAC-SHA256: a deliberately slow, password-specific hash. Every password gets its own random
# salt, so two people with the same password get different hashes and precomputed ("rainbow") tables
# are useless. The stored text records the scheme, round count and salt, so it can be checked later
# and the round count raised over time:  pbkdf2_sha256$<rounds>$<salt>$<hash>
SCHEME = "pbkdf2_sha256"
ROUNDS = 600_000  # OWASP's 2023 recommendation for PBKDF2-SHA256
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ROUNDS)
    return f"{SCHEME}${ROUNDS}${salt}${digest.hex()}"


# Accounts made before this code existed were saved as  pbkdf2_sha256$<salt>$<hash>  with no round count
# written down, so we try the round counts such systems normally use. A match logs the person in and
# their hash is rewritten in the new format (see needs_rehash), so each old account only needs this once.
LEGACY_ROUNDS = (1_000, 10_000, 50_000, 100_000, 120_000, 150_000, 200_000, 260_000, 310_000, 390_000, 480_000, 600_000)


def _salt_forms(salt: str) -> list[bytes]:
    """The salt as plain text, plus the ways it may have been encoded (hex or base64)."""
    forms = [salt.encode()]
    for decode in (bytes.fromhex, lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)), lambda s: base64.b64decode(s + "=" * (-len(s) % 4))):
        try:
            forms.append(decode(salt))
        except ValueError:
            pass
    return forms


def verify_password(password: str, stored: str) -> bool:
    """True if `password` matches the stored hash (current format or the older one)."""
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == SCHEME and parts[1].isdigit():
        _, rounds, salt, expected = parts
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds))
        return hmac.compare_digest(digest.hex(), expected)  # constant-time compare
    if len(parts) == 3 and parts[0] == SCHEME:
        _, salt, expected = parts
        for salt_bytes in _salt_forms(salt):
            for rounds in LEGACY_ROUNDS:
                digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_bytes, rounds)
                if hmac.compare_digest(digest.hex(), expected):
                    return True
    return False


def needs_rehash(stored: str) -> bool:
    parts = stored.split("$")
    return len(parts) != 4 or not parts[1].isdigit() or int(parts[1]) < ROUNDS


# A real hash to check against when an email is unknown, so "no such account" takes as long as
# "wrong password" and the response time doesn't reveal which emails are registered.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


# ---------- tokens ----------
def new_token() -> str:
    """A long random secret for a session cookie or a reset link."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Only this fingerprint is saved in the database, so a stolen database can't be used to log in."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- password rules ----------
MIN_LENGTH = 10
MAX_LENGTH = 64  # also keeps the work per login bounded

# rule id -> what to tell the person (the website shows the same list as a checklist)
RULES = {
    "length": f"{MIN_LENGTH} to {MAX_LENGTH} characters",
    "lower": "a lowercase letter",
    "upper": "an uppercase letter",
    "digit": "a number",
    "special": "a symbol, like ! ? # $ %",
    "not_common": "nothing easy to guess, like “password” or “123456”",
    "not_personal": "no part of your name or email",
}

COMMON_PARTS = ("password", "passw0rd", "qwerty", "letmein", "welcome", "iloveyou", "admin", "abc123", "123456", "111111", "000000")


def failed_rules(password: str, email: str = "", first_name: str = "", last_name: str = "") -> list[str]:
    """The ids of the rules this password breaks (an empty list means it is fine)."""
    low = password.lower()
    bad = []
    if not MIN_LENGTH <= len(password) <= MAX_LENGTH:
        bad.append("length")
    if not re.search(r"[a-z]", password):
        bad.append("lower")
    if not re.search(r"[A-Z]", password):
        bad.append("upper")
    if not re.search(r"\d", password):
        bad.append("digit")
    if not re.search(r"[^A-Za-z0-9\s]", password):
        bad.append("special")
    if any(part in low for part in COMMON_PARTS) or re.search(r"(.)\1{3,}", password):
        bad.append("not_common")
    personal = [email.split("@")[0].lower(), first_name.lower(), last_name.lower()]
    if any(len(p) >= 3 and p in low for p in personal):
        bad.append("not_personal")
    return bad
