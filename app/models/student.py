from typing import Optional

from sqlmodel import Field, SQLModel


class Student(SQLModel, table=True):
    student_id: Optional[int] = Field(default=None, primary_key=True)
    # --- student-build:snippet Student ---
    name: str = Field(max_length=100, nullable=False)
    degreeID: int = Field(foreign_key="degree.degree_id", nullable=False)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    # --- end snippet ---
