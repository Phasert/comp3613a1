from typing import Optional

from sqlmodel import Field, SQLModel


class PlanCourse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    CourseID: int
    plan_id: int = Field(foreign_key="studentplan.plan_id")
    year: int
    semester: str = ""
    name: str = ""
    status: str = ""
    credits: int = 0
