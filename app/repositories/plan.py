from datetime import date
from typing import Optional

from sqlmodel import Session, select

from app.models.degree import Degree
from app.models.plan_course import PlanCourse
from app.models.student import Student
from app.models.student_plan import StudentPlan


class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_degrees(self) -> list[Degree]:
        return list(self.db.exec(select(Degree).order_by(Degree.name)).all())

    def get_degree(self, degree_id: int) -> Optional[Degree]:
        return self.db.get(Degree, degree_id)

    def get_student_by_user_id(self, user_id: int) -> Optional[Student]:
        return self.db.exec(
            select(Student).where(Student.user_id == user_id)
        ).one_or_none()

    def add_student(self, name: str, degree_id: int, user_id: int) -> Student:
        student = Student(name=name, degreeID=degree_id, user_id=user_id)
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)
        return student

    def update_student_degree(self, student: Student, degree_id: int) -> Student:
        student.degreeID = degree_id
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)
        return student

    def add_plan(self, student_id: int, status: str, progress: str = "") -> StudentPlan:
        plan = StudentPlan(
            student_id=student_id,
            date=date.today(),
            progress=progress,
            status=status,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def add_plan_course(self, plan_id: int, course: dict) -> PlanCourse:
        row = PlanCourse(
            CourseID=int(course["CourseID"]),
            plan_id=plan_id,
            year=int(course["year"]),
            semester=str(course["semester"]),
            name=str(course["name"]),
            status=str(course.get("status") or ""),
            credits=int(course.get("credits") or 0),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_latest_plan(self, student_id: int) -> Optional[StudentPlan]:
        return self.db.exec(
            select(StudentPlan)
            .where(StudentPlan.student_id == student_id)
            .order_by(StudentPlan.plan_id.desc())
        ).first()

    def list_plan_courses(self, plan_id: int) -> list[PlanCourse]:
        return list(
            self.db.exec(
                select(PlanCourse)
                .where(PlanCourse.plan_id == plan_id)
                .order_by(PlanCourse.year, PlanCourse.semester, PlanCourse.name)
            ).all()
        )
