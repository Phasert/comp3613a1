from typing import Optional

from app.models.advisor import Advisor
from app.models.plan_course import PlanCourse
from app.models.query_review import QueryReview
from app.models.review_plan import ReviewPlan
from app.models.student_plan import StudentPlan
from app.repositories.advisor import (
    AdvisorRepository,
    QueryReviewRepository,
    ReviewPlanRepository,
)
from app.repositories.plan import PlanRepository

DECISIONS = ("", "Approve", "Reject", "Additional Help")
PENDING = "pending"
REVIEWED = "reviewed"
WAITING = "waiting on assistance"


class AdvisorService:
    """Application rules for the advisor side: queue, review, help requests."""

    def __init__(
        self,
        plan_repo: PlanRepository,
        advisor_repo: AdvisorRepository,
        review_repo: ReviewPlanRepository,
        query_repo: QueryReviewRepository,
    ):
        self.plan_repo = plan_repo
        self.advisor_repo = advisor_repo
        self.review_repo = review_repo
        self.query_repo = query_repo

    # —— advisor identity ——

    def advisor_for_user(self, user_id: int) -> Optional[Advisor]:
        return self.advisor_repo.get_by_user_id(user_id)

    def advisers_in_faculty(self, faculty: str) -> list[Advisor]:
        return self.advisor_repo.list_all(faculty=faculty)

    def all_advisers(self) -> list[Advisor]:
        """Every advisor on staff, for the Request Help dropdowns."""
        return self.advisor_repo.list_all()

    def all_faculties(self) -> list[str]:
        """Every faculty that runs a degree programme."""
        return sorted({d.faculty for d in self.plan_repo.list_degrees() if d.faculty})

    # —— the review queue (counts derived from ReviewPlan history) ——

    def queue(self, advisor: Advisor) -> dict:
        """Submissions for the advisor's faculty.

        Only plans the student actually submitted appear here. Pending Review is
        how many decisions are still outstanding, Reviewed how many reviews have
        been submitted, and Resubmitted how many plans have been reviewed more
        than once (the student came back with a new submission).
        """
        rows = []
        counts = {"pending": 0, "reviewed": 0, "resubmitted": 0}
        for row in self.plan_repo.list_plans_for_faculty(advisor.faculty):
            plan = row["plan"]
            if plan.status == "not submitted":
                continue  # saved by the student, never sent for review
            reviews = self.review_repo.count_for_plan(plan.plan_id)
            if plan.status == REVIEWED:
                counts["reviewed"] += 1
            elif plan.status == PENDING:
                counts["pending"] += 1
            if reviews >= 2:
                counts["resubmitted"] += 1
            state = plan.status
            # A plan with a student question waiting is shown as Query.
            latest = self.review_repo.latest_for_plan(plan.plan_id)
            if latest and any(
                q.kind == "question" and q.progress == "open"
                for q in self.query_repo.list_for_review(latest.review_id)
            ):
                state = "query"
            courses = self.plan_repo.list_plan_courses(plan.plan_id)
            years = sorted({c.year for c in courses})
            rows.append(
                {
                    "plan": plan,
                    "student": row["student"],
                    "degree": row["degree"],
                    "state": state,
                    "reviews": reviews,
                    "year_label": f"Year {years[0]}" if years else "Plan",
                    "course_count": len(courses),
                }
            )
        return {"rows": rows, "counts": counts}

    # —— reviewing one plan ——

    def open_plan(self, advisor: Advisor, plan_id: int) -> Optional[dict]:
        """Load a plan for review, recording that this advisor received it."""
        found = next(
            (
                row
                for row in self.plan_repo.list_plans_for_faculty(advisor.faculty)
                if row["plan"].plan_id == plan_id
            ),
            None,
        )
        if not found:
            return None
        plan = found["plan"]
        review = self.review_repo.latest_for_plan(plan_id)
        if plan.status == PENDING and review is None:
            review = self.review_repo.add_review(plan_id, advisor.staff_id)
        courses = self.plan_repo.list_plan_courses(plan_id)
        return {
            "plan": plan,
            "student": found["student"],
            "degree": found["degree"],
            "review": review,
            "groups": self.course_groups(courses),
            "latest_query": self.latest_query_for_plan(plan_id),
        }

    def record_review(
        self,
        advisor: Advisor,
        plan_id: int,
        decisions: dict,
        note: str,
        submit: bool,
    ) -> Optional[ReviewPlan]:
        """Store the per-course decisions and (on Submit) close the review."""
        opened = self.open_plan(advisor, plan_id)
        if not opened:
            return None
        for course_row_id, decision in decisions.items():
            clean = str(decision or "")
            if clean not in DECISIONS:
                clean = ""
            self.plan_repo.set_course_decision(int(course_row_id), clean)
        review = opened["review"]
        if not review:
            review = self.review_repo.add_review(plan_id, advisor.staff_id, note)
        else:
            review = self.review_repo.set_note(review.review_id, note)
        if submit:
            self.plan_repo.set_plan_status(plan_id, REVIEWED)
        return review

    # —— help requests ——

    def request_help(
        self, advisor: Advisor, plan_id: int, faculty: str, asked_staff_id: int, reason: str
    ) -> Optional[QueryReview]:
        opened = self.open_plan(advisor, plan_id)
        if not opened or not opened["review"]:
            return None
        query = self.query_repo.add_query(
            opened["review"].review_id, opened["plan"].student_id, reason
        )
        # The plan now waits on the advisor who was asked to answer.
        self.plan_repo.set_plan_status(plan_id, WAITING)
        return query

    def assistance(self, query_id: int) -> Optional[dict]:
        query = self.query_repo.get(query_id)
        if not query:
            return None
        review = self.review_repo.get(query.review_id)
        plan = self.plan_repo.get_plan(review.plan_id) if review else None
        if not plan:
            return None
        return {
            "query": query,
            "review": review,
            "plan": plan,
            "student": self.plan_repo.get_student(plan.student_id),
            "degree": self.plan_repo.get_degree(getattr(plan, "degree_id", 0) or 0),
            "requester": self.advisor_repo.get(review.staff_id) if review else None,
            "groups": self.course_groups(self.plan_repo.list_plan_courses(plan.plan_id)),
        }

    def answer_assistance(self, query_id: int, response: str) -> Optional[QueryReview]:
        """Answering a request sends it back to the advisor who asked for it."""
        help_request = self.assistance(query_id)
        if not help_request:
            return None
        query = self.query_repo.set_response(query_id, response, "answered")
        self.plan_repo.set_plan_status(help_request["plan"].plan_id, PENDING)
        return query

    def query_rows(self, advisor: Advisor) -> list[dict]:
        """Queries this advisor can act on.

        An assistance request is open to the faculty; a student question goes
        only to the advisor who reviewed that plan. Answered queries are kept
        as history.
        """
        rows = []
        for query in self.query_repo.list_all():
            review = self.review_repo.get(query.review_id)
            if not review:
                continue
            kind = getattr(query, "kind", "assistance")
            mine = review.staff_id == advisor.staff_id
            if kind == "question" and not mine:
                continue
            student = self.plan_repo.get_student(query.student_id)
            advisor = self.advisor_repo.get(review.staff_id)
            plan = self.plan_repo.get_plan(review.plan_id)
            # a student question is asked by the student, not by the advisor
            asked_by = (student.name if student else "—") if kind == "question" else (
                advisor.name if advisor else "—"
            )
            rows.append(
                {
                    "query": query,
                    "kind": kind,
                    "plan": plan,
                    "student": student,
                    "requester": advisor,
                    "asked_by": asked_by,
                }
            )
        return rows

    def latest_query_for_plan(self, plan_id: int) -> Optional[dict]:
        """The most recent help request/answer on this plan, with who it was asked from."""
        review = self.review_repo.latest_for_plan(plan_id)
        if not review:
            return None
        queries = [q for q in self.query_repo.list_all() if q.review_id == review.review_id]
        if not queries:
            return None
        return {
            "query": queries[-1],
            "kind": getattr(queries[-1], "kind", "assistance"),
            "requester": self.advisor_repo.get(review.staff_id),
        }

    def course_groups(self, courses: list) -> list[dict]:
        """Years, then semesters inside them — the same shape the student sees."""
        groups: list[dict] = []
        for year in sorted({c.year for c in courses}):
            rows = [c for c in courses if c.year == year]
            labels: list[str] = []
            for c in sorted(rows, key=lambda c: c.semester):
                if c.semester not in labels:
                    labels.append(c.semester)
            groups.append(
                {
                    "year": year,
                    "semesters": [
                        {
                            "label": label,
                            "rows": [c for c in rows if c.semester == label],
                        }
                        for label in labels
                    ],
                }
            )
        return groups