import json

from fastapi import Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.plan import PlanRepository
from app.services.plan_service import PlanService
from app.utilities.flash import flash

from . import router, templates


def _plan_service(db) -> PlanService:
    return PlanService(PlanRepository(db))


def _draft(request: Request) -> dict:
    return request.session.get("draft_plan") or {
        "degree_id": None,
        "faculty": "",
        "department": "",
        "courses": [],
    }


@router.get("/app/plans/new", name="create_plan_start")
async def create_plan_start(request: Request, user: AuthDep):
    request.session["draft_plan"] = {
        "degree_id": None,
        "faculty": "",
        "department": "",
        "courses": [],
    }
    return RedirectResponse(
        url=request.url_for("plan_details_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/app/plans/new/details", response_class=HTMLResponse, name="plan_details_view")
async def plan_details_view(request: Request, user: AuthDep, db: SessionDep):
    service = _plan_service(db)
    return templates.TemplateResponse(
        request=request,
        name="plan_details.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "degrees": service.list_degrees(),
            "draft": _draft(request),
            "nav_create": True,
        },
    )


@router.post("/app/plans/new/details", name="plan_details_save")
async def plan_details_save(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    faculty: str = Form(),
    department: str = Form(),
    degree_id: int = Form(),
):
    service = _plan_service(db)
    degree = service.get_degree(degree_id)
    draft = _draft(request)
    draft["faculty"] = faculty
    draft["department"] = department
    draft["degree_id"] = degree_id
    if degree:
        draft["faculty"] = degree.faculty
        draft["department"] = degree.department
        draft["requirements"] = degree.requirements
        draft["degree_name"] = degree.name
    request.session["draft_plan"] = draft
    return RedirectResponse(
        url=request.url_for("plan_courses_view").include_query_params(year=1),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/app/plans/new/courses", response_class=HTMLResponse, name="plan_courses_view")
async def plan_courses_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    year: int = 1,
):
    service = _plan_service(db)
    draft = _draft(request)
    selected = {
        int(c["CourseID"])
        for c in draft.get("courses", [])
        if int(c.get("year") or 0) == year
    }
    return templates.TemplateResponse(
        request=request,
        name="plan_courses.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "draft": draft,
            "year": year,
            "catalog": service.catalog_for_year(year),
            "selected_ids": selected,
            "credits_obtained": sum(
                int(c.get("credits") or 0)
                for c in draft.get("courses", [])
                if int(c.get("year") or 0) == year
            ),
            "nav_create": True,
        },
    )


@router.post("/app/plans/new/courses", name="plan_courses_save")
async def plan_courses_save(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = _plan_service(db)
    form = await request.form()
    year = int(form.get("year") or 1)
    picked = set(form.getlist("course_id"))
    draft = _draft(request)
    kept = [c for c in draft.get("courses", []) if int(c.get("year") or 0) != year]
    catalog = service.catalog_for_year(year)
    for semester, rows in catalog.items():
        for row in rows:
            if str(row["CourseID"]) in picked:
                kept.append(
                    {
                        "CourseID": row["CourseID"],
                        "year": year,
                        "semester": semester,
                        "name": row["name"],
                        "credits": row["credits"],
                        "status": "",
                    }
                )
    draft["courses"] = kept
    request.session["draft_plan"] = draft
    nxt = form.get("next") or "next"
    if nxt == "back":
        if year <= 1:
            dest = request.url_for("plan_details_view")
        else:
            dest = request.url_for("plan_courses_view").include_query_params(year=year - 1)
    elif year < 3:
        dest = request.url_for("plan_courses_view").include_query_params(year=year + 1)
    else:
        dest = request.url_for("plan_review_view")
    return RedirectResponse(url=dest, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/app/plans/current", response_class=HTMLResponse, name="current_plan_view")
async def current_plan_view(request: Request, user: AuthDep, db: SessionDep):
    service = _plan_service(db)
    plan = service.latest_plan_for_user(user.id)
    if not plan:
        flash(request, "No saved plan yet.", "info")
        return RedirectResponse(
            url=request.url_for("user_home_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    courses = service.courses_for_plan(plan.plan_id)
    years = {}
    for course in courses:
        years.setdefault(course.year, []).append(course)
    return templates.TemplateResponse(
        request=request,
        name="plan_current.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "plan": plan,
            "years": years,
            "total_credits": sum(c.credits for c in courses),
            "nav_create": True,
        },
    )


@router.get("/app/plans/new/review", response_class=HTMLResponse, name="plan_review_view")
async def plan_review_view(request: Request, user: AuthDep, db: SessionDep):
    service = _plan_service(db)
    draft = _draft(request)
    courses = draft.get("courses") or []
    years = {}
    for course in courses:
        years.setdefault(int(course["year"]), []).append(course)
    return templates.TemplateResponse(
        request=request,
        name="plan_review.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "draft": draft,
            "years": years,
            "total_credits": sum(int(c.get("credits") or 0) for c in courses),
            "courses_json": json.dumps(courses),
            "nav_create": True,
        },
    )


@router.post("/app/plans", response_class=HTMLResponse, name="create_plan_save")
async def create_plan_save(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    action: str = Form(),
    degree_id: int = Form(),
    courses: str = Form(),
):
    # --- student-build:snippet create_plan_save ---
    repository = PlanRepository(db)
    service = PlanService(repository)

    service.create_plan(
        user_id=user.id,
        degree_id=degree_id,
        courses=courses,
        action=action,
    )
    # --- end snippet ---
    request.session.pop("draft_plan", None)
    flash(
        request,
        "Plan submitted for approval." if action == "submit" else "Plan saved.",
        "success",
    )
    return RedirectResponse(
        url=request.url_for("user_home_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
