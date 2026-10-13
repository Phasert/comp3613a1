from typing import Optional

from sqlmodel import Field, SQLModel


class Advisor(SQLModel, table=True):
    staff_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    faculty: str = ""
    # Nullable: an advisor can exist as staff (and be asked for help in the
    # Request Help dropdown) without having a login account of their own.
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)