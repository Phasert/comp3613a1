from typing import Optional

from sqlmodel import Field, SQLModel


class QueryReview(SQLModel, table=True):
    """A student question or an advisor assistance request tied to one review."""
    query_id: Optional[int] = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="reviewplan.review_id")
    student_id: int = Field(foreign_key="student.student_id")
    question: str = ""
    response: str = ""
    progress: str = "open"

    # --- student-build:snippet QueryReview-kind ---
    # TODO: one short text field telling the two apart — a student question
    # (answered by the advisor who reviewed that plan) and an advisor
    # assistance request (open to the faculty). PlanService asks the queries
    # for it, so keep the field name `kind` and the values below.
    #   kind = "question"   — the student asked, that reviewer answers
    #   kind = "assistance" — one advisor asked another for help
    kind: str = Field(default="question", max_length=20)
    # --- end snippet ---