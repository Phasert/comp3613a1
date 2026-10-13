from typing import Optional

from sqlmodel import Session, select

from app.models.advisor import Advisor
from app.models.query_review import QueryReview
from app.models.review_plan import ReviewPlan


class AdvisorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: int) -> Optional[Advisor]:
        return self.db.exec(
            select(Advisor).where(Advisor.user_id == user_id)
        ).one_or_none()

    def get(self, staff_id: int) -> Optional[Advisor]:
        return self.db.get(Advisor, staff_id)

    def list_all(self, faculty: str = "") -> list[Advisor]:
        statement = select(Advisor).order_by(Advisor.name)
        if faculty:
            statement = statement.where(Advisor.faculty == faculty)
        return list(self.db.exec(statement).all())

    def add(self, name: str, faculty: str, user_id: int) -> Advisor:
        advisor = Advisor(name=name, faculty=faculty, user_id=user_id)
        self.db.add(advisor)
        self.db.commit()
        self.db.refresh(advisor)
        return advisor


class ReviewPlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_review(self, plan_id: int, staff_id: int, note: str = "") -> ReviewPlan:
        from datetime import date

        review = ReviewPlan(plan_id=plan_id, staff_id=staff_id, note=note, date=date.today())
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def get(self, review_id: int) -> Optional[ReviewPlan]:
        return self.db.get(ReviewPlan, review_id)

    def list_for_plan(self, plan_id: int) -> list[ReviewPlan]:
        return list(
            self.db.exec(
                select(ReviewPlan)
                .where(ReviewPlan.plan_id == plan_id)
                .order_by(ReviewPlan.review_id)
            ).all()
        )

    def count_for_plan(self, plan_id: int) -> int:
        return len(self.list_for_plan(plan_id))

    def latest_for_plan(self, plan_id: int) -> Optional[ReviewPlan]:
        reviews = self.list_for_plan(plan_id)
        return reviews[-1] if reviews else None

    def set_note(self, review_id: int, note: str) -> ReviewPlan:
        review = self.db.get(ReviewPlan, review_id)
        review.note = note
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review


class QueryReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_query(
        self, review_id: int, student_id: int, question: str, kind: str = "assistance"
    ) -> QueryReview:
        query = QueryReview(
            review_id=review_id,
            student_id=student_id,
            question=question,
            response="",
            progress="open",
            kind=kind,
        )
        self.db.add(query)
        self.db.commit()
        self.db.refresh(query)
        return query

    def get(self, query_id: int) -> Optional[QueryReview]:
        return self.db.get(QueryReview, query_id)

    def set_response(self, query_id: int, response: str, progress: str) -> QueryReview:
        query = self.db.get(QueryReview, query_id)
        query.response = response
        query.progress = progress
        self.db.add(query)
        self.db.commit()
        self.db.refresh(query)
        return query

    def list_for_review(self, review_id: int) -> list[QueryReview]:
        return list(
            self.db.exec(
                select(QueryReview)
                .where(QueryReview.review_id == review_id)
                .order_by(QueryReview.query_id)
            ).all()
        )

    def get_for_student(self, query_id: int, student_id: int) -> Optional[QueryReview]:
        """A query that belongs to this student (None if it does not)."""
        query = self.db.get(QueryReview, query_id)
        if not query or query.student_id != student_id:
            return None
        return query

    def list_all(self) -> list[QueryReview]:
        return list(self.db.exec(select(QueryReview).order_by(QueryReview.query_id)).all())