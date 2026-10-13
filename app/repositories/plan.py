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

    def get_student(self, student_id: int) -> Optional[Student]:
        return self.db.get(Student, student_id)

    def get_plan(self, plan_id: int) -> Optional[StudentPlan]:
        return self.db.get(StudentPlan, plan_id)

    def delete_plan_courses(self, plan_id: int) -> int:
        rows = self.db.exec(
            select(PlanCourse).where(PlanCourse.plan_id == plan_id)
        ).all()
        for row in rows:
            self.db.delete(row)
        self.db.commit()
        return len(rows)

    def set_plan_status(
        self, plan_id: int, status: str, minor: str = "", degree_id: int = 0
    ) -> StudentPlan:
        plan = self.db.get(StudentPlan, plan_id)
        plan.status = status
        plan.minor = minor or plan.minor
        if degree_id:
            plan.degree_id = degree_id
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

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

    def add_plan(
        self,
        student_id: int,
        status: str,
        progress: str = "",
        minor: str = "",
        degree_id: int = 0,
    ) -> StudentPlan:
        plan = StudentPlan(
            student_id=student_id,
            date=date.today(),
            progress=progress,
            status=status,
            minor=minor,
            degree_id=degree_id,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def add_plan_course(self, plan_id: int, course: dict) -> PlanCourse:
        row = PlanCourse(
            plan_id=plan_id,
            code=str(course.get("code") or ""),
            name=str(course.get("name") or ""),
            credits=int(course.get("credits") or 0),
            type=str(course.get("type") or ""),
            level=str(course.get("level") or ""),
            status=str(course.get("status") or "To Do"),
            decision=str(course.get("decision") or ""),
            year=int(course.get("year") or 1),
            semester=str(course.get("semester") or "1"),
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

    def list_plans_for_faculty(self, faculty: str) -> list[dict]:
        """Plans built for a degree in this faculty, newest first.

        The faculty comes from the degree on the *plan*, not from the student,
        so a later plan choosing another major cannot move earlier plans.
        """
        statement = (
            select(StudentPlan, Student, Degree)
            .join(Student, StudentPlan.student_id == Student.student_id)
            .join(Degree, StudentPlan.degree_id == Degree.degree_id)
            .where(Degree.faculty == faculty)
            .order_by(StudentPlan.plan_id.desc())
        )
        rows = []
        for plan, student, degree in self.db.exec(statement).all():
            rows.append({"plan": plan, "student": student, "degree": degree})
        return rows

    def list_plans_with_degree(self, student_id: int) -> list[dict]:
        """A student's plans, each with the degree that plan was built for."""
        statement = (
            select(StudentPlan, Degree)
            .join(Degree, StudentPlan.degree_id == Degree.degree_id)
            .where(StudentPlan.student_id == student_id)
            .order_by(StudentPlan.plan_id.desc())
        )
        return [
            {"plan": plan, "degree": degree} for plan, degree in self.db.exec(statement).all()
        ]

    def set_course_decision(self, course_row_id: int, decision: str) -> PlanCourse:
        row = self.db.get(PlanCourse, course_row_id)
        row.decision = decision
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def latest_review_for_plan(self, plan_id: int) -> dict:
        """The most recent advisor review on a plan, with the advisor's name."""
        from app.models.advisor import Advisor
        from app.models.review_plan import ReviewPlan

        statement = (
            select(ReviewPlan, Advisor)
            .join(Advisor, ReviewPlan.staff_id == Advisor.staff_id)
            .where(ReviewPlan.plan_id == plan_id)
            .order_by(ReviewPlan.review_id.desc())
        )
        row = self.db.exec(statement).first()
        if not row:
            return {}
        review, advisor = row[0], row[1]
        return {"note": review.note, "date": review.date, "advisor": advisor.name}

    def latest_review_id(self, plan_id: int) -> int:
        """The id of the most recent review on a plan (0 if never reviewed)."""
        from app.models.review_plan import ReviewPlan

        review = self.db.exec(
            select(ReviewPlan)
            .where(ReviewPlan.plan_id == plan_id)
            .order_by(ReviewPlan.review_id.desc())
        ).first()
        return review.review_id if review else 0

    def latest_review_by_id(self, review_id: int):
        """One review row, by id."""
        from app.models.review_plan import ReviewPlan

        return self.db.get(ReviewPlan, review_id)
