"""Learning from mistakes: when a customer says the chatbot showed the wrong kind of thing ("I asked for sleeveless
and you showed me a hoodie"), the chatbot saves a LESSON, and the shop applies it to every later search.

A lesson is not free text that gets pasted into the instructions. It has a fixed, checked shape:
    customer_term   what customers say                  ("sleeveless")
    not_these       garment types that are wrong for it  ("pullover hoodie")
    try_instead     the closest garment types we carry   ("short-sleeve t-shirt")
    note            one short sentence of why
and the garment types must be real ones from the catalogue. That keeps a customer from teaching the chatbot something
harmful. A lesson starts "pending" and becomes "active" once TWO DIFFERENT customers have reported it (or an admin
approves it), so one person can't quietly change what everybody sees. Active lessons are enforced by the search tool
itself, and shown to the chatbot as data.
"""

import json
import re

import auth
import catalogue
from models import Lesson, LessonSaved

ACTIVATE_AFTER = 2  # different customers who must report the same lesson
MAX_TERM = 40
MAX_NOTE = 200
TERM = re.compile(r"^[a-z][a-z \-']{1,%d}$" % (MAX_TERM - 1))


def ensure_tables() -> None:
    with auth.db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS search_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_term TEXT NOT NULL,
                not_these TEXT NOT NULL,
                try_instead TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'disabled')),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (customer_term, not_these)
            );
            CREATE TABLE IF NOT EXISTS lesson_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER NOT NULL,
                reporter TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (lesson_id, reporter),
                FOREIGN KEY (lesson_id) REFERENCES search_lessons(id)
            );
            """
        )


def real_types() -> list[str]:
    return sorted({p.garment_type for p in catalogue.load_products()})


def _match_types(names: list[str]) -> tuple[list[str], list[str]]:
    """Maps what the AI typed onto real garment types. Returns (matched, unknown)."""
    real, matched, unknown = real_types(), [], []
    for name in names:
        n = " ".join(name.lower().split())
        hit = next((t for t in real if t.lower() == n), None)
        if hit is None:
            unknown.append(name)
        elif hit not in matched:
            matched.append(hit)
    return matched, unknown


def _row_to_lesson(row, reports: int) -> Lesson:
    return Lesson(id=row["id"], customer_term=row["customer_term"], not_these=json.loads(row["not_these"]), try_instead=json.loads(row["try_instead"]),
                  note=row["note"], status=row["status"], reports=reports)


def save(reporter: str, term: str, not_these: list[str], try_instead: list[str], note: str = "") -> LessonSaved:
    term = " ".join(term.lower().split())
    if not TERM.match(term):
        return LessonSaved(saved=False, message="The term must be a short word or phrase made of letters, like 'sleeveless'.")
    wrong, bad1 = _match_types(not_these)
    right, bad2 = _match_types(try_instead)
    if bad1 or bad2:
        return LessonSaved(saved=False, message=f"These aren't garment types we carry: {bad1 + bad2}. Use list_styles for the real ones.")
    if not wrong:
        return LessonSaved(saved=False, message="Say at least one garment type that was wrong for it.")
    if set(wrong) & set(right):
        return LessonSaved(saved=False, message="A garment type can't be both wrong and right for the same term.")
    note = " ".join(note.split())[:MAX_NOTE]
    wrong_json, right_json = json.dumps(sorted(wrong)), json.dumps(sorted(right))
    with auth.db() as conn:
        row = conn.execute("SELECT * FROM search_lessons WHERE customer_term = ? AND not_these = ?", (term, wrong_json)).fetchone()
        if row is None:
            lesson_id = conn.execute("INSERT INTO search_lessons (customer_term, not_these, try_instead, note) VALUES (?, ?, ?, ?)", (term, wrong_json, right_json, note)).lastrowid
        else:
            lesson_id = row["id"]
        conn.execute("INSERT OR IGNORE INTO lesson_reports (lesson_id, reporter) VALUES (?, ?)", (lesson_id, reporter))
        reports = conn.execute("SELECT COUNT(*) FROM lesson_reports WHERE lesson_id = ?", (lesson_id,)).fetchone()[0]
        status = conn.execute("SELECT status FROM search_lessons WHERE id = ?", (lesson_id,)).fetchone()["status"]
        if status == "pending" and reports >= ACTIVATE_AFTER:
            conn.execute("UPDATE search_lessons SET status = 'active' WHERE id = ?", (lesson_id,))
            status = "active"
    where = "I'll use it for everyone from now on." if status == "active" else "I'll start using it for everyone once another customer confirms it."
    return LessonSaved(saved=True, status=status, message=f"Saved what we learned about '{term}'. {where}")


def _contains(text: str, term: str) -> bool:
    return re.search(r"\b" + re.escape(term) + r"\b", text.lower()) is not None


def active() -> list[Lesson]:
    with auth.db() as conn:
        rows = conn.execute("SELECT * FROM search_lessons WHERE status = 'active' ORDER BY id").fetchall()
        return [_row_to_lesson(r, conn.execute("SELECT COUNT(*) FROM lesson_reports WHERE lesson_id = ?", (r["id"],)).fetchone()[0]) for r in rows]


def matching(text: str) -> list[Lesson]:
    """The active lessons whose term appears in this text."""
    return [l for l in active() if _contains(text, l.customer_term)]


def all_lessons() -> list[Lesson]:
    with auth.db() as conn:
        rows = conn.execute("SELECT * FROM search_lessons ORDER BY status = 'active' DESC, id DESC").fetchall()
        return [_row_to_lesson(r, conn.execute("SELECT COUNT(*) FROM lesson_reports WHERE lesson_id = ?", (r["id"],)).fetchone()[0]) for r in rows]


def set_status(lesson_id: int, status: str) -> bool:
    with auth.db() as conn:
        return conn.execute("UPDATE search_lessons SET status = ? WHERE id = ?", (status, lesson_id)).rowcount > 0
