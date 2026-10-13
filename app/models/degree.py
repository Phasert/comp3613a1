from typing import Optional

from sqlmodel import Field, SQLModel


class Degree(SQLModel, table=True):
    degree_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    credits: int = 0
    faculty: str = ""
    department: str = ""
    requirements: str = ""

    # --- student-build:snippet Degree-requirements ---
    # TODO: numeric requirement counts for the Review "courses still needed"
    # lines (Core / Level I / Level II). PlanService.requirements_summary
    core_required: int = Field(default=0)
    level1_required: int = Field(default=0)
    level2_required: int = Field(default=0)
    # reads `core_required`, `level1_required`, `level2_required`.
    # --- end snippet ---
