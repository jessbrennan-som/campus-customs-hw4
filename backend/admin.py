"""For the shop's admins: the customer feedback the chatbot collected, ready to read.

Only logged-in customers whose email is listed in the ADMIN_EMAILS setting (see config.py) can use these routes.
With nobody listed they stay closed. They show feedback only: first names and last initials, never emails,
passwords or contact details.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import auth
import lessons
import memory
from config import ADMIN_EMAILS
from models import Lesson, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


class FeedbackEntry(BaseModel):
    id: int
    product_id: str
    product_name: str
    customer: str  # first name and last initial
    rating: int | None
    fit: str | None
    comment: str
    created_at: str


class FeedbackSummary(BaseModel):
    product_id: str
    product_name: str
    responses: int
    average_rating: float | None
    runs_small: int
    true_to_size: int
    runs_large: int
    latest: str


def admin_only(user: User = Depends(auth.current_user)) -> User:
    if user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(403, "This area is for the shop's admins.")
    return user


@router.get("/feedback", response_model=list[FeedbackEntry])
def feedback(limit: int = Query(200, ge=1, le=1000), _: User = Depends(admin_only)):
    """Every piece of customer feedback, newest first."""
    return memory.all_feedback(limit)


@router.get("/feedback/summary", response_model=list[FeedbackSummary])
def summary(_: User = Depends(admin_only)):
    """One line per product: how many customers answered, the average rating, and how it fits."""
    return memory.feedback_summary()


@router.get("/lessons", response_model=list[Lesson])
def lessons_list(_: User = Depends(admin_only)):
    """What the chatbot has learned from customers' corrections: pending ones waiting for a second customer or an
    admin, active ones the shop is using, and any switched off."""
    return lessons.all_lessons()


@router.post("/lessons/{lesson_id}/{action}")
def lesson_action(lesson_id: int, action: str, _: User = Depends(admin_only)):
    """approve (start using it now), disable (stop using it) or reset (back to waiting)."""
    status = {"approve": "active", "disable": "disabled", "reset": "pending"}.get(action)
    if status is None or not lessons.set_status(lesson_id, status):
        raise HTTPException(404, "No such lesson or action.")
    return {"id": lesson_id, "status": status}
