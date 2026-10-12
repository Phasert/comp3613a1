"""Database table models.

Import every table model here so ``SQLModel.metadata.create_all`` sees them.
"""

from app.models.degree import Degree
from app.models.plan_course import PlanCourse
from app.models.student import Student
from app.models.student_plan import StudentPlan
from app.models.user import User

__all__ = ["User", "Degree", "Student", "StudentPlan", "PlanCourse"]
