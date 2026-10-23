"""Sends email. With SMTP settings in the environment it sends for real; without them (the default
while developing) it saves each email as a text file in the outbox folder so you can read it."""

import os
import re
import smtplib
import time
from email.message import EmailMessage

from config import OUTBOX_DIR


def send_email(to: str, subject: str, body: str) -> str:
    """Returns "sent" or "outbox" so callers and tests know what happened."""
    host = os.getenv("SMTP_HOST")
    if host:
        msg = EmailMessage()
        msg["From"] = os.getenv("SMTP_FROM", "Campus Customs <no-reply@campuscustoms.example>")
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=20) as smtp:
            smtp.starttls()
            if os.getenv("SMTP_USER"):
                smtp.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            smtp.send_message(msg)
        return "sent"

    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9@._-]", "_", to)
    path = OUTBOX_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{safe}.txt"
    path.write_text(f"To: {to}\nSubject: {subject}\n\n{body}\n")
    print(f"[email not sent: no SMTP_HOST set] saved to {path}")
    return "outbox"
