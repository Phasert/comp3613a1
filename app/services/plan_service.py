import json
from typing import Optional

from app.models.degree import Degree
from app.models.student import Student
from app.models.student_plan import StudentPlan
from app.repositories.plan import PlanRepository

COURSE_CATALOG = {
    1: {
        "1": [
            {"CourseID": 1601, "name": "COMP 1601", "credits": 3},
            {"CourseID": 1602, "name": "COMP 1602", "credits": 3},
            {"CourseID": 1115, "name": "MATH 1115", "credits": 3},
        ],
        "2": [
            {"CourseID": 1603, "name": "COMP 1603", "credits": 3},
            {"CourseID": 1604, "name": "COMP 1604", "credits": 3},
            {"CourseID": 1116, "name": "MATH 1116", "credits": 3},
        ],
    },
    2: {
        "1": [
            {"CourseID": 2601, "name": "COMP 2601", "credits": 3},
            {"CourseID": 2602, "name": "COMP 2602", "credits": 3},
            {"CourseID": 2605, "name": "COMP 2605", "credits": 3},
        ],
        "2": [
            {"CourseID": 2603, "name": "COMP 2603", "credits": 3},
            {"CourseID": 2604, "name": "COMP 2604", "credits": 3},
        ],
    },
    3: {
        "1": [
            {"CourseID": 3601, "name": "COMP 3601", "credits": 3},
            {"CourseID": 3602, "name": "COMP 3602", "credits": 3},
            {"CourseID": 3603, "name": "COMP 3603", "credits": 3},
        ],
        "2": [
            {"CourseID": 3605, "name": "COMP 3605", "credits": 3},
            {"CourseID": 3606, "name": "COMP 3606", "credits": 3},
        ],
    },
}


class PlanService:
    def __init__(self, plan_repo: PlanRepository):
        self.plan_repo = plan_repo

    def list_degrees(self) -> list[Degree]:
        return self.plan_repo.list_degrees()

    def get_degree(self, degree_id: int) -> Optional[Degree]:
        return self.plan_repo.get_degree(degree_id)

    def get_student_for_user(self, user_id: int) -> Optional[Student]:
        return self.plan_repo.get_student_by_user_id(user_id)

    def catalog_for_year(self, year: int) -> dict:
        return COURSE_CATALOG.get(year, {})

    def latest_plan_for_user(self, user_id: int) -> Optional[StudentPlan]:
        student = self.plan_repo.get_student_by_user_id(user_id)
        if not student:
            return None
        return self.plan_repo.get_latest_plan(student.student_id)

    def courses_for_plan(self, plan_id: int):
        return self.plan_repo.list_plan_courses(plan_id)

    def create_plan(self, user_id: int, degree_id: int, courses, action: str):
        # --- student-build:snippet create_plan ---
        student = self.plan_repo.get_student_by_user_id(user_id)
        if not student:
            raise ValueError("Student not found for user_id: {}".format(user_id))

        self.plan_repo.update_student_degree(student, degree_id)
        status = "not submitted" if action == "save" else "pending"
        

        plan = self.plan_repo.add_plan(student.student_id, status=status)
        for course in courses:
            self.plan_repo.add_plan_course(plan.plan_id, course)
        
        return plan

        # --- end snippet ---
