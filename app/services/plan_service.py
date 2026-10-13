from typing import Optional

from app.models.degree import Degree
from app.models.student import Student
from app.models.student_plan import StudentPlan
from app.repositories.plan import PlanRepository

LEVELS = ("I", "II", "III")
STATUSES = ("To Do", "Passed", "Fail")
COURSE_TYPES = ("Core", "Elective", "Minor")
DEFAULT_SEMESTERS = ("1", "2")
DEFAULT_ROWS_PER_SEMESTER = 3
NEW_SEMESTER_FALLBACK = "Summer"


def blank_draft() -> dict:
    return {
        "degree_id": None,
        "degree_name": "",
        "faculty": "",
        "department": "",
        "requirements": "",
        "minor": "",
        "years": [1],
        "year_semesters": {"1": list(DEFAULT_SEMESTERS)},
        "courses": [],
    }


class PlanService:
    def __init__(self, plan_repo: PlanRepository, query_repo=None):
        self.plan_repo = plan_repo
        self.query_repo = query_repo

    # —— database lookups ——

    def list_degrees(self) -> list[Degree]:
        return self.plan_repo.list_degrees()

    def faculties(self, degrees: list[Degree]) -> list[str]:
        return sorted({d.faculty for d in degrees if d.faculty})

    def departments(self, degrees: list[Degree]) -> list[dict]:
        seen = {}
        for d in degrees:
            if d.department:
                seen.setdefault(
                    (d.faculty, d.department),
                    {"name": d.department, "faculty": d.faculty},
                )
        return sorted(seen.values(), key=lambda row: (row["faculty"], row["name"]))

    def get_degree(self, degree_id: int) -> Optional[Degree]:
        return self.plan_repo.get_degree(degree_id)

    def get_student_for_user(self, user_id: int) -> Optional[Student]:
        return self.plan_repo.get_student_by_user_id(user_id)

    def latest_plan_for_user(self, user_id: int) -> Optional[StudentPlan]:
        student = self.plan_repo.get_student_by_user_id(user_id)
        if not student:
            return None
        return self.plan_repo.get_latest_plan(student.student_id)

    def courses_for_plan(self, plan_id: int):
        return self.plan_repo.list_plan_courses(plan_id)

    def plan_by_id(self, user_id: int, plan_id: int) -> Optional[StudentPlan]:
        """A plan the signed-in student actually owns (None if it is not theirs)."""
        student = self.plan_repo.get_student_by_user_id(user_id)
        if not student:
            return None
        plan = self.plan_repo.get_plan(plan_id)
        if not plan or plan.student_id != student.student_id:
            return None
        return plan

    def advisor_review_note(self, plan_id: int) -> dict:
        """The advisor's note on this plan, for the student's saved-plan view."""
        return self.plan_repo.latest_review_for_plan(plan_id)

    # —— the student's queries about a reviewed plan ——

    def queries_for_plan(self, plan_id: int) -> list:
        """The queries this student has raised against their latest review."""
        review_id = self.plan_repo.latest_review_id(plan_id)
        if not review_id or not self.query_repo:
            return []
        return self.query_repo.list_for_review(review_id)

    def can_query(self, plan) -> bool:
        """A query is only meaningful once an advisor has finished reviewing.

        While a plan is `pending` (submitted, waiting on a decision) or
        `waiting on assistance`, the student has nothing to query yet.
        """
        return plan.status == "reviewed"

    def can_continue(self, plan) -> bool:
        """Continue is for a plan the student owns the timing on.

        A saved plan (`not submitted`) is theirs to finish; a `reviewed` plan is
        theirs to add to — a year-2 addition, say, or marking courses passed —
        and send back for review. While a plan is `pending` or
        `waiting on assistance` it is with the advisor, so there is nothing to
        continue.
        """
        return plan.status in ("not submitted", "reviewed")

    def continue_destination(self, plan) -> str:
        """Where Continue leads: finish a saved plan at the review page, or
        add to a reviewed plan in Course Selection first."""
        return "review" if plan.status == "not submitted" else "edit"

    def plan_to_continue(self, user_id: int, plan_id: int) -> Optional[StudentPlan]:
        """The plan the student is allowed to continue, or None."""
        plan = self.plan_by_id(user_id, plan_id)
        if not plan or not self.can_continue(plan):
            return None
        return plan

    def ask_query(self, user_id: int, plan_id: int, question: str):
        """Send a student question to the advisor who reviewed that plan."""
        student = self.plan_repo.get_student_by_user_id(user_id)
        plan = self.plan_by_id(user_id, plan_id)
        if not student or not plan or not question.strip():
            return None
        review_id = self.plan_repo.latest_review_id(plan_id)
        if not review_id:
            return None  # nobody has reviewed this plan yet, so nobody can answer
        return self.query_repo.add_query(
            review_id, student.student_id, question.strip(), kind="question"
        )

    def query_for_student(self, user_id: int, query_id: int):
        """A query the signed-in student owns, with the plan it belongs to."""
        student = self.plan_repo.get_student_by_user_id(user_id)
        if not student:
            return None
        query = self.query_repo.get_for_student(query_id, student.student_id)
        if not query:
            return None
        review = self.plan_repo.latest_review_by_id(query.review_id)
        if not review:
            return None
        plan = self.plan_repo.get_plan(review.plan_id)
        if not plan:
            return None
        return {"query": query, "plan": plan, "review": review}

    # —— draft rules (the in-progress plan held in the session) ——

    def save_details(
        self,
        draft: dict,
        *,
        faculty: str,
        department: str,
        degree_id: int,
        minor: str,
    ) -> dict:
        degree = self.get_degree(degree_id)
        draft["degree_id"] = degree_id
        draft["faculty"] = degree.faculty if degree else faculty
        draft["department"] = degree.department if degree else department
        draft["degree_name"] = degree.name if degree else ""
        draft["requirements"] = degree.requirements if degree else ""
        minor = (minor or "").strip()
        draft["minor"] = minor
        return draft

    def years(self, draft: dict) -> list[int]:
        years = {int(y) for y in draft.get("years") or [1]}
        return sorted(years or {1})

    def max_year(self, draft: dict) -> int:
        return max(self.years(draft))

    def semesters_for_year(self, draft: dict, year: int) -> list[str]:
        store = draft.setdefault("year_semesters", {})
        key = str(year)
        labels = store.get(key)
        if not labels:
            labels = list(DEFAULT_SEMESTERS)
            store[key] = labels
        return labels

    def add_year(self, draft: dict) -> int:
        new_year = self.max_year(draft) + 1
        draft["years"] = sorted(set(self.years(draft)) | {new_year})
        self.semesters_for_year(draft, new_year)
        return new_year

    def remove_year(self, draft: dict, year: int) -> None:
        years = self.years(draft)
        if year <= 1 or len(years) <= 1:
            return
        draft["years"] = [y for y in years if y != year]
        draft.setdefault("year_semesters", {}).pop(str(year), None)
        draft["courses"] = [
            c for c in draft.get("courses", []) if int(c.get("year") or 0) != year
        ]

    def add_semester(self, draft: dict, year: int, label: str = "") -> str:
        labels = self.semesters_for_year(draft, year)
        label = (label or "").replace(":", "").strip()
        if not label:
            label = (
                NEW_SEMESTER_FALLBACK
                if NEW_SEMESTER_FALLBACK not in labels
                else str(len(labels) + 1)
            )
        if label in labels:
            return label
        labels.append(label)
        return label

    def remove_semester(self, draft: dict, year: int, label: str) -> None:
        labels = self.semesters_for_year(draft, year)
        if len(labels) <= 1 or label not in labels:
            return
        labels.remove(label)
        draft["courses"] = [
            c
            for c in draft.get("courses", [])
            if not (
                int(c.get("year") or 0) == year
                and str(c.get("semester") or "") == str(label)
            )
        ]

    def rows_for(self, draft: dict, year: int, semester: str) -> list[dict]:
        rows = [
            dict(c)
            for c in draft.get("courses", [])
            if int(c.get("year") or 0) == year
            and str(c.get("semester") or "") == str(semester)
        ]
        while len(rows) < DEFAULT_ROWS_PER_SEMESTER:
            rows.append(
                {
                    "code": "",
                    "name": "",
                    "credits": "",
                    "type": "",
                    "level": "",
                    "status": "To Do",
                    "year": year,
                    "semester": str(semester),
                }
            )
        return rows

    def _clean_row(self, raw: dict, year: int, semester: str) -> Optional[dict]:
        code = str(raw.get("code") or "").strip()
        name = str(raw.get("name") or "").strip()
        if not code and not name:
            return None
        try:
            credits = int(raw.get("credits") or 0)
        except (TypeError, ValueError):
            credits = 0
        level = str(raw.get("level") or "")
        if level not in LEVELS:
            level = ""
        status = str(raw.get("status") or "")
        if status not in STATUSES:
            status = "To Do"
        course_type = str(raw.get("type") or "")
        if course_type not in COURSE_TYPES:
            course_type = ""
        return {
            "code": code,
            "name": name,
            "credits": credits,
            "type": course_type,
            "level": level,
            "status": status,
            "decision": "",
            "year": year,
            "semester": str(semester),
        }

    def save_courses(self, draft: dict, rows: list[dict]) -> None:
        cleaned = []
        for raw in rows:
            row = self._clean_row(
                raw,
                int(raw.get("year") or 1),
                str(raw.get("semester") or "1"),
            )
            if row:
                cleaned.append(row)
        draft["courses"] = cleaned

    # —— credits: a semester counts only courses marked Passed; otherwise N/A ——

    def passed_credits(
        self, draft: dict, year: Optional[int] = None, semester: str = ""
    ) -> int:
        total = 0
        for c in draft.get("courses", []):
            if c.get("status") != "Passed":
                continue
            if year is not None and int(c.get("year") or 0) != year:
                continue
            if semester and str(c.get("semester") or "") != str(semester):
                continue
            total += int(c.get("credits") or 0)
        return total

    def has_passed(self, draft: dict, year: int, semester: str) -> bool:
        return any(
            c.get("status") == "Passed"
            and int(c.get("year") or 0) == year
            and str(c.get("semester") or "") == str(semester)
            for c in draft.get("courses", [])
        )

    def semester_credits(self, draft: dict, year: int, semester: str) -> Optional[int]:
        """Passed credits for a semester, or None when nothing is passed (shown as N/A)."""
        if not self.has_passed(draft, year, semester):
            return None
        return self.passed_credits(draft, year, semester)

    def year_credits(self, draft: dict, year: int) -> Optional[int]:
        """Passed credits for a year, or None when nothing is passed (shown as N/A)."""
        rows = [
            c for c in draft.get("courses", []) if int(c.get("year") or 0) == year
        ]
        if not any(c.get("status") == "Passed" for c in rows):
            return None
        return self.passed_credits(draft, year=year)

    def course_page(self, draft: dict) -> list[dict]:
        max_year = self.max_year(draft)
        sections = []
        for year in self.years(draft):
            labels = self.semesters_for_year(draft, year)
            sections.append(
                {
                    "year": year,
                    "is_last": year == max_year,
                    "removable": year > 1 and len(self.years(draft)) > 1,
                    "semesters": [
                        {
                            "label": label,
                            "rows": self.rows_for(draft, year, label),
                            "credits": self.semester_credits(draft, year, label),
                            "removable": len(labels) > 1,
                        }
                        for label in labels
                    ],
                    "credits": self.year_credits(draft, year),
                }
            )
        return sections

    def grouped(self, draft: dict) -> list[tuple[int, list[tuple[str, list[dict]]]]]:
        out = []
        for year in self.years(draft):
            semesters = []
            for label in self.semesters_for_year(draft, year):
                rows = [
                    c
                    for c in draft.get("courses", [])
                    if int(c.get("year") or 0) == year
                    and str(c.get("semester") or "") == label
                ]
                semesters.append((label, rows))
            out.append((year, semesters))
        return out

    # —— requirements: one line per category on the Review page ——

    MINOR_REQUIRED = 2
    MINOR_LEVEL_II_REDUCTION = 2

    def requirements_line(self, draft: dict) -> str:
        """Human-readable requirement text, adjusted for a typed minor."""
        degree = self.get_degree(draft.get("degree_id") or 0)
        if not degree:
            return draft.get("requirements") or ""
        core = int(degree.core_required or 0)
        level1 = int(degree.level1_required or 0)
        level2 = int(degree.level2_required or 0)
        minor = (draft.get("minor") or "").strip()
        if minor:
            level2 = max(level2 - self.MINOR_LEVEL_II_REDUCTION, 0)
        parts = []
        if core:
            parts.append(f"{core} core courses")
        if level1:
            parts.append(f"{level1} level I electives")
        if level2:
            parts.append(f"{level2} level II electives")
        if minor:
            parts.append(f"{self.MINOR_REQUIRED} minor courses")
        return ", ".join(parts) or (degree.requirements or "")

    def requirements_summary(self, draft: dict) -> list[dict]:
        """One line per requirement category. A minor drops the Level II
        requirement by MINOR_LEVEL_II_REDUCTION and adds a Minor line.
        Only courses marked Passed count towards a category.
        """
        degree = self.get_degree(draft.get("degree_id") or 0)
        core_req = int(degree.core_required or 0) if degree else 0
        level1_req = int(degree.level1_required or 0) if degree else 0
        level2_req = int(degree.level2_required or 0) if degree else 0
        minor = (draft.get("minor") or "").strip()
        if minor:
            level2_req = max(level2_req - self.MINOR_LEVEL_II_REDUCTION, 0)

        counts = {"core": 0, "level_i": 0, "level_ii": 0, "minor": 0}
        for c in draft.get("courses", []):
            if c.get("status") != "Passed":
                continue
            course_type = str(c.get("type") or "")
            level = str(c.get("level") or "")
            if course_type == "Minor":
                counts["minor"] += 1
            elif course_type == "Core":
                counts["core"] += 1
            elif level == "I":
                counts["level_i"] += 1
            elif level == "II":
                counts["level_ii"] += 1

        rows = [
            ("Core courses", counts["core"], core_req),
            ("Level I electives", counts["level_i"], level1_req),
            ("Level II electives", counts["level_ii"], level2_req),
        ]
        if minor:
            rows.append(("Minor courses", counts["minor"], self.MINOR_REQUIRED))
        return [
            {
                "label": label,
                "passed": passed,
                "required": required,
                "remaining": max(required - passed, 0),
            }
            for label, passed, required in rows
        ]

    def requirements_progress(self, draft: dict) -> dict:
        """Overall progress plus the per-category lines used by the progress bar."""
        rows = self.requirements_summary(draft)
        required = sum(r["required"] for r in rows)
        passed = min(sum(r["passed"] for r in rows), required)
        return {
            "rows": rows,
            "passed": passed,
            "required": required,
            "percent": round(100 * passed / required) if required else 0,
        }

    def plans_for_user(self, user_id: int) -> list[dict]:
        """One summary row per saved plan, for the My Plan card list."""
        student = self.plan_repo.get_student_by_user_id(user_id)
        if not student:
            return []
        summaries = []
        for row in self.plan_repo.list_plans_with_degree(student.student_id):
            plan = row["plan"]
            degree = row["degree"]
            courses = self.plan_repo.list_plan_courses(plan.plan_id)
            years = sorted({c.year for c in courses})
            summaries.append(
                {
                    "plan": plan,
                    "year_label": f"Year {years[0]} plan" if years else "Plan",
                    "degree_name": degree.name if degree else "",
                    "course_count": len(courses),
                    "can_query": self.can_query(plan) and not any(
                q.progress == "open" for q in self.queries_for_plan(plan.plan_id)
            ),
                    "can_continue": self.can_continue(plan),
                    "continue_to": self.continue_destination(plan),
                    "passed_credits": sum(
                        c.credits for c in courses if c.status == "Passed"
                    ),
                    "total_credits": sum(c.credits for c in courses),
                }
            )
        return summaries

    def plan_draft(self, user_id: int, plan: StudentPlan) -> dict:
        """Rebuild the editable draft from a saved plan.

        The same draft shape is used by Course Selection, Review and the
        saved-plan progress view, so the requirement rules apply everywhere.
        """
        draft = blank_draft()
        student = self.plan_repo.get_student_by_user_id(user_id)
        degree = self.get_degree(getattr(plan, "degree_id", 0) or 0)
        if not degree and student and student.degreeID:
            degree = self.get_degree(student.degreeID)
        if degree:
            draft["degree_id"] = degree.degree_id
            draft["degree_name"] = degree.name
            draft["faculty"] = degree.faculty
            draft["department"] = degree.department
            draft["requirements"] = degree.requirements
        draft["plan_id"] = plan.plan_id
        draft["minor"] = plan.minor or ""
        courses = self.plan_repo.list_plan_courses(plan.plan_id)
        draft["years"] = sorted({c.year for c in courses}) or [1]
        for year in draft["years"]:
            labels = []
            for c in sorted(
                (c for c in courses if c.year == year), key=lambda c: c.semester
            ):
                if c.semester not in labels:
                    labels.append(c.semester)
            draft["year_semesters"][str(year)] = labels or list(DEFAULT_SEMESTERS)
        draft["courses"] = [
            {
                "code": c.code,
                "name": c.name,
                "credits": c.credits,
                "type": c.type or "",
                "level": c.level or "",
                "status": c.status or "To Do",
                "decision": c.decision or "",
                "year": c.year,
                "semester": c.semester,
            }
            for c in courses
        ]
        return draft

    def saved_plan_groups(self, draft: dict) -> list[dict]:
        """Saved-plan view of the course rows, keyed for the template."""
        return [
            {
                "year": year,
                "semesters": [
                    {
                        "label": label,
                        "rows": [
                            c
                            for c in draft["courses"]
                            if c["year"] == year and c["semester"] == label
                        ],
                        "credits": self.semester_credits(draft, year, label),
                    }
                    for label in self.semesters_for_year(draft, year)
                ],
            }
            for year in self.years(draft)
        ]

    # —— persistence ——

    def create_plan(
        self,
        *,
        user_id: int,
        student_name: str,
        degree_id: int,
        minor: str,
        courses: list,
        action: str,
        plan_id: Optional[int] = None,
    ) -> StudentPlan:
        # --- student-build:snippet create_plan ---
        rows = [r for r in (courses or []) if r]

        student = self.plan_repo.get_student_by_user_id(user_id)
        if not student:
            student = self.plan_repo.add_student(student_name, degree_id, user_id)
        elif not student.degreeID:
            # First plan for this student also sets their enrolled programme.
            self.plan_repo.update_student_degree(student, degree_id)

        status = "not submitted" if action == "save" else "pending"
        existing = self.plan_repo.get_plan(plan_id) if plan_id else None
        if existing and existing.student_id == student.student_id:
            # Continuing a saved plan updates it instead of creating a duplicate.
            plan = self.plan_repo.set_plan_status(
                plan_id, status, minor=(minor or "").strip(), degree_id=degree_id
            )
            self.plan_repo.delete_plan_courses(plan.plan_id)
        else:
            plan = self.plan_repo.add_plan(
                student.student_id,
                status=status,
                minor=(minor or "").strip(),
                degree_id=degree_id,
            )
        for course in rows:
            self.plan_repo.add_plan_course(plan.plan_id, course)
        return plan
        # --- end snippet ---
