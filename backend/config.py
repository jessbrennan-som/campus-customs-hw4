"""Settings shared by the whole API. Secrets come from environment variables (or a .env file), never from code."""

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# find_dotenv(usecwd=True) walks up from the folder you run the server in until it finds a .env file.
load_dotenv(find_dotenv(usecwd=True))

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR.parent / "data"
DB_PATH = Path(os.getenv("CAMPUS_DB", DATA_DIR / "campus_customs.db"))
IMAGE_DIR = DATA_DIR / "products"  # the original photos
WHITE_DIR = DATA_DIR / "products-white"  # the same photos with white backgrounds (see whiten_images.py)

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # quiet the startup banner

# The chatbot's AI model, reached through Portkey. The key comes from the class-wide .env, never from code.
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY", "")
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
CHAT_MODEL = os.getenv("SHOP_MODEL", "gpt-5.6-luna")
PROMPT_FILE = BACKEND_DIR / "prompt" / "prompt.md"

# Where the website lives, so password-reset emails can link back to it.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ALLOWED_ORIGINS = [FRONTEND_URL, "http://127.0.0.1:5173"]

# Login sessions
SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"  # set to 1 once the site is served over https

# Password reset
RESET_MINUTES = 30

# Admins (people who may read customer feedback): a comma-separated list of emails in the ADMIN_EMAILS setting.
# With none set, nobody is an admin and the admin routes stay closed.
ADMIN_EMAILS = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}

# Email. With no SMTP_HOST set, emails are written to the outbox folder instead of being sent.
OUTBOX_DIR = Path(os.getenv("CC_OUTBOX", BACKEND_DIR / "outbox"))

# The audit trail: an append-only record of what the chatbot's agent loop did (see audit.py).
AUDIT_FILE = Path(os.getenv("AUDIT_TRAIL", BACKEND_DIR.parent / "output" / "audit_trail.json"))
