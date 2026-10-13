from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class StudentPlan(SQLModel, table=True):
    plan_id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.student_id")
    date: date
    progress: str = ""
    status: str = "not submitted"

    # --- student-build:snippet StudentPlan-degree ---
    # TODO: each plan must remember the major it was built for, so choosing a
    # different degree on a new plan cannot move the plans already submitted
    # or reviewed. One FK to the degree table — keep the field name `degree_id`
    # (PlanRepository.add_plan and list_plans_for_faculty read it).
    degree_id: int = Field(foreign_key="degree.degree_id")
    # --- end snippet ---

    # --- student-build:snippet StudentPlan ---
    # TODO: store the minor chosen on Plan Details (a degree name, or blank for none).
    minor: str = Field(default="", max_length=100)
    # --- end snippet ---
