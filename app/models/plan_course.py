from typing import Optional

from sqlmodel import Field, SQLModel


class PlanCourse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="studentplan.plan_id")

    # --- student-build:snippet PlanCourse ---
    # TODO: add the course row fields agreed in the redesign:
    code: str = Field(default="", max_length=10)
    name: str = Field(default="", max_length=100)
    credits: int = Field(default=0)
    level: str = Field(default="", max_length=3)
    status: str = Field(default="To Do", max_length=20)
    decision: str = Field(default="", max_length=20)
    year: int = Field(default=1)
    semester: str = Field(default="1", max_length=10)
    # typed course code, name, credits, level (I / II / III),
    # the student's status, the advisor's decision, year, semester.
    # (PlanRepository.add_plan_course already writes to these field names.)
    # --- end snippet ---

    # --- student-build:snippet PlanCourse-type ---
    # TODO: the new "Course type" column on Course Selection
    type: str = Field(default="", max_length=20)
    # (Core / Elective / Minor). PlanRepository.add_plan_course writes `type`.
    # --- end snippet ---
