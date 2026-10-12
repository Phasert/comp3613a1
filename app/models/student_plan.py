from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class StudentPlan(SQLModel, table=True):
    plan_id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.student_id")
    date: date
    progress: str = ""
    status: str = "not submitted"
