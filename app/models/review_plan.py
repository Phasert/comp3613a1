from datetime import date as Date
from typing import Optional

from sqlmodel import Field, SQLModel


class ReviewPlan(SQLModel, table=True):
    review_id: Optional[int] = Field(default=None, primary_key=True)

    # --- student-build:snippet ReviewPlan ---

    plan_id: int = Field(foreign_key="studentplan.plan_id")
    staff_id: int = Field(foreign_key="advisor.staff_id")
    note: str = Field(default="", max_length=1000)
    date: Date = Field(default_factory=Date.today)
    # --- end snippet ---