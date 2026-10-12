from typing import Optional

from sqlmodel import Field, SQLModel


class Degree(SQLModel, table=True):
    degree_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    credits: int = 0
    faculty: str = ""
    department: str = ""
    requirements: str = ""
