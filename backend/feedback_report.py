"""Compiles the customer feedback the chatbot collected into one readable report for the shop's admins.

    cd backend
    source .venv/bin/activate
    python feedback_report.py            # writes ../output/customer_feedback.md

It reads the customer_feedback table (and the product_feedback_summary view). Customers appear as a first
name and last initial only: no emails or other contact details.
"""

import argparse
from datetime import date
from pathlib import Path

import lessons
import memory

STARS = {1: "★☆☆☆☆", 2: "★★☆☆☆", 3: "★★★☆☆", 4: "★★★★☆", 5: "★★★★★"}
FITS = {"runs_small": "runs small", "true_to_size": "true to size", "runs_large": "runs large"}


def build_report() -> str:
    return _feedback_section() + _lessons_section()


def _lessons_section() -> str:
    found = lessons.all_lessons()
    out = ["", "# What the chatbot has learned", ""]
    if not found:
        return "\n".join(out + ["No lessons yet. They appear here when customers tell Handsome Dan a result was the wrong kind of thing."]) + "\n"
    out += ["| Customers say | Not these | Closest we carry | Customers who reported | Status |", "| --- | --- | --- | --- | --- |"]
    for l in found:
        out.append(f"| {l.customer_term} | {', '.join(l.not_these)} | {', '.join(l.try_instead) or 'none'} | {l.reports} | {l.status} |")
    return "\n".join(out) + "\n"


def _feedback_section() -> str:
    memory.ensure_tables()
    lessons.ensure_tables()
    summary = memory.feedback_summary()
    entries = memory.all_feedback(1000)
    lines = ["# Customer feedback", "", f"Compiled {date.today():%B %d, %Y} from what customers told Handsome Dan about products they bought.", ""]
    if not entries:
        return "\n".join(lines + ["No feedback yet. It appears here as customers answer \"How did it work out?\" in the chat."]) + "\n"

    rated = [e["rating"] for e in entries if e["rating"]]
    lines += [
        f"**{len(entries)} {'response' if len(entries) == 1 else 'responses'}** across **{len(summary)} {'product' if len(summary) == 1 else 'products'}**"
        + (f", average rating **{sum(rated) / len(rated):.1f} / 5**." if rated else "."),
        "",
        "## By product",
        "",
        "| Product | Responses | Average rating | Runs small | True to size | Runs large | Latest |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in summary:
        avg = f"{s['average_rating']:.1f}" if s["average_rating"] is not None else "n/a"
        lines.append(f"| {s['product_name']} | {s['responses']} | {avg} | {s['runs_small'] or 0} | {s['true_to_size'] or 0} | {s['runs_large'] or 0} | {s['latest'][:10]} |")
    lines += ["", "## Every response, newest first", ""]
    for e in entries:
        bits = [STARS[e["rating"]] if e["rating"] else None, FITS.get(e["fit"] or ""), e["created_at"][:10]]
        lines.append(f"- **{e['product_name']}**, {e['customer']} ({', '.join(b for b in bits if b)}): {e['comment']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the customer feedback report.")
    parser.add_argument("--out", help="where to write it (default: ../output/customer_feedback.md)")
    args = parser.parse_args()
    target = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "output" / "customer_feedback.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text(build_report())
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
