from typing import Optional

from fastapi import Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.advisor import QueryReviewRepository
from app.repositories.plan import PlanRepository
from app.services.plan_service import PlanService, blank_draft
from app.utilities.flash import flash

from . import router, templates


def _plan_service(db) -> PlanService:
    return PlanService(PlanRepository(db), QueryReviewRepository(db))


def _draft(request: Request) -> dict:
    return request.session.get("draft_plan") or blank_draft()


def _redirect(url, fragment: str = "") -> RedirectResponse:
    return RedirectResponse(
        url=f"{url}#{fragment}" if fragment else url,
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/app/plans/new", name="create_plan_start")
async def create_plan_start(request: Request, user: AuthDep):
    request.session["draft_plan"] = blank_draft()
    return RedirectResponse(
        url=request.url_for("plan_details_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/app/plans/new/details", response_class=HTMLResponse, name="plan_details_view")
async def plan_details_view(request: Request, user: AuthDep, db: SessionDep):
    service = _plan_service(db)
    degrees = service.list_degrees()
    draft = _draft(request)
    return templates.TemplateResponse(
        request=request,
        name="plan_details.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "degrees": degrees,
            "faculties": service.faculties(degrees),
            "departments": service.departments(degrees),
            "draft": draft,
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
    minor: str = Form(""),
):
    service = _plan_service(db)
    draft = _draft(request)
    service.save_details(
        draft,
        faculty=faculty,
        department=department,
        degree_id=degree_id,
        minor=minor,
    )
    request.session["draft_plan"] = draft
    return RedirectResponse(
        url=str(request.url_for("plan_courses_view")) + "#year-1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/app/plans/new/courses", response_class=HTMLResponse, name="plan_courses_view")
async def plan_courses_view(request: Request, user: AuthDep, db: SessionDep):
    service = _plan_service(db)
    draft = _draft(request)
    return templates.TemplateResponse(
        request=request,
        name="plan_courses.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "draft": draft,
            "sections": service.course_page(draft),
            "req_line": service.requirements_line(draft),
            "levels": ["I", "II", "III"],
            "statuses": ["To Do", "Passed", "Fail"],
            "course_types": ["Core", "Elective", "Minor"],
            "nav_create": True,
        },
    )


@router.post("/app/plans/new/courses", name="plan_courses_save")
async def plan_courses_save(request: Request, user: AuthDep, db: SessionDep):
    service = _plan_service(db)
    form = await request.form()

    year_values = form.getlist("year")
    semester_values = form.getlist("semester")
    codes = form.getlist("code")
    names = form.getlist("name")
    credits = form.getlist("credits")
    types = form.getlist("type")
    levels = form.getlist("level")
    statuses = form.getlist("status")
    rows = [
        {
            "year": year_values[i] if i < len(year_values) else 1,
            "semester": semester_values[i] if i < len(semester_values) else "1",
            "code": codes[i] if i < len(codes) else "",
            "name": names[i] if i < len(names) else "",
            "credits": credits[i] if i < len(credits) else 0,
            "type": types[i] if i < len(types) else "",
            "level": levels[i] if i < len(levels) else "",
            "status": statuses[i] if i < len(statuses) else "",
        }
        for i in range(
            max(len(year_values), len(codes), len(names), len(semester_values))
        )
    ]

    draft = _draft(request)
    service.save_courses(draft, rows)

    intent = str(form.get("intent") or "continue")
    parts = intent.split(":")
    action = parts[0]
    courses_url = str(request.url_for("plan_courses_view"))

    fragment = ""
    if action == "add_year":
        new_year = service.add_year(draft)
        fragment = f"year-{new_year}"
    elif action == "remove_year" and len(parts) > 1:
        service.remove_year(draft, int(parts[1]))
        fragment = f"year-{service.max_year(draft)}"
    elif action == "add_semester" and len(parts) > 1:
        year = int(parts[1])
        service.add_semester(draft, year, str(form.get(f"label_{year}") or ""))
        fragment = f"year-{year}"
    elif action == "remove_semester" and len(parts) > 2:
        year = int(parts[1])
        service.remove_semester(draft, year, parts[2])
        fragment = f"year-{year}"

    request.session["draft_plan"] = draft

    if action == "back":
        return RedirectResponse(
            url=request.url_for("plan_details_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if action == "continue":
        return RedirectResponse(
            url=request.url_for("plan_review_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return _redirect(courses_url, fragment)


@router.get("/app/plans", response_class=HTMLResponse, name="my_plans_view")
async def my_plans_view(request: Request, user: AuthDep, db: SessionDep):
    service = _plan_service(db)
    return templates.TemplateResponse(
        request=request,
        name="plan_list.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "summaries": service.plans_for_user(user.id),
            "nav_my_plans": True,
        },
    )


@router.get("/app/plans/current", response_class=HTMLResponse, name="current_plan_view")
async def current_plan_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    plan_id: Optional[int] = None,
):
    service = _plan_service(db)
    plan = (
        service.plan_by_id(user.id, plan_id)
        if plan_id
        else service.latest_plan_for_user(user.id)
    )
    if not plan:
        flash(request, "No saved plan yet.", "info")
        return RedirectResponse(
            url=request.url_for("user_home_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    draft = service.plan_draft(user.id, plan)
    return templates.TemplateResponse(
        request=request,
        name="plan_current.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "plan": plan,
            "degree_name": draft.get("degree_name", ""),
            "groups": service.saved_plan_groups(draft),
            "progress": service.requirements_progress(draft),
            "review": service.advisor_review_note(plan.plan_id),
            "queries": service.queries_for_plan(plan.plan_id),
            "can_query": service.can_query(plan)
            and not any(q.progress == "open" for q in service.queries_for_plan(plan.plan_id)),
            "can_continue": service.can_continue(plan),
            "continue_to": service.continue_destination(plan),
            "nav_my_plans": True,
        },
    )


@router.get("/app/plans/current/query", response_class=HTMLResponse, name="plan_query_view")
async def plan_query_view(
    request: Request, user: AuthDep, db: SessionDep, plan_id: int
):
    service = _plan_service(db)
    plan = service.plan_by_id(user.id, plan_id)
    if not plan:
        flash(request, "That plan is not available.", "danger")
        return RedirectResponse(
            url=request.url_for("my_plans_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if not service.can_query(plan):
        flash(
            request,
            "You can query an advisor once this plan has been reviewed.",
            "info",
        )
        return RedirectResponse(
            url=request.url_for("current_plan_view").include_query_params(
                plan_id=plan.plan_id
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        request=request,
        name="plan_query.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "plan": plan,
            "review": service.advisor_review_note(plan.plan_id),
            "queries": service.query_repo.list_all() if service.query_repo else [],
            "nav_my_plans": True,
        },
    )


@router.post("/app/plans/current/query", name="plan_query_save")
async def plan_query_save(request: Request, user: AuthDep, db: SessionDep):
    # --- student-build:snippet plan_query_save ---
    # TODO: bind the submitted form and ask the service to send the question to
    # the advisor who reviewed that plan. Thin route: no SQL here.
    service = _plan_service(db)
    form = await request.form()

    question = str(form.get("question") or "").strip()
    plan_id = int(form.get("plan_id") or 0)

    query = service.ask_query(user.id, plan_id, question)
    if not query:
        flash(request, "Could not send that question.", "danger")
        return _redirect(str(request.url_for("plan_query_view").include_query_params(plan_id=plan_id)))
    # --- end snippet ---
    return _student_query_redirect(request, query)


@router.get("/app/plans/query/{query_id}", response_class=HTMLResponse, name="plan_query_detail_view")
async def plan_query_detail_view(
    request: Request, user: AuthDep, db: SessionDep, query_id: int
):
    service = _plan_service(db)
    asked = service.query_for_student(user.id, query_id)
    if not asked:
        flash(request, "That query is not available.", "danger")
        return RedirectResponse(
            url=request.url_for("my_plans_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    draft = service.plan_draft(user.id, asked["plan"])
    return templates.TemplateResponse(
        request=request,
        name="plan_query_detail.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "asked": asked,
            "review": service.advisor_review_note(asked["plan"].plan_id),
            "groups": service.saved_plan_groups(draft),
            "nav_my_plans": True,
        },
    )


def _student_query_redirect(request: Request, query=None):
    """After asking, go to the question so the student can see it was sent."""
    if query is not None:
        return RedirectResponse(
            url=str(request.url_for("plan_query_detail_view", query_id=query.query_id)),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(
        url=request.url_for("my_plans_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/app/plans/current/continue", name="plan_continue_view")
async def plan_continue_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    plan_id: int,
    to: str = "",
):
    """Load a saved plan back into the draft so it can be finished or added to.

    A `not submitted` plan continues at the final review page; a `reviewed`
    plan opens in Course Selection so the student can add to it (a year-2
    addition, or marking courses passed) and send it back for review. While the
    plan is with an advisor there is nothing to continue.
    """
    service = _plan_service(db)
    plan = service.plan_to_continue(user.id, plan_id)
    if not plan:
        flash(request, "This plan is with your advisor right now.", "info")
        return RedirectResponse(
            url=request.url_for("my_plans_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    request.session["draft_plan"] = service.plan_draft(user.id, plan)
    destination = (
        request.url_for("plan_courses_view")
        if to == "edit"
        else request.url_for("plan_review_view")
    )
    return RedirectResponse(url=destination, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/app/plans/new/review", response_class=HTMLResponse, name="plan_review_view")
async def plan_review_view(request: Request, user: AuthDep, db: SessionDep):
    service = _plan_service(db)
    draft = _draft(request)
    years = service.years(draft)
    return templates.TemplateResponse(
        request=request,
        name="plan_review.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "draft": draft,
            "grouped": service.grouped(draft),
            "year_credits": {y: service.year_credits(draft, y) for y in years},
            "semester_credits": {
                (y, s): service.semester_credits(draft, y, s)
                for y in years
                for s in service.semesters_for_year(draft, y)
            },
            "total_credits": service.passed_credits(draft),
            "requirements": service.requirements_summary(draft),
            "progress": service.requirements_progress(draft),
            "req_line": service.requirements_line(draft),
            "max_year": service.max_year(draft),
            "nav_create": True,
        },
    )


@router.post("/app/plans", response_class=HTMLResponse, name="create_plan_save")
async def create_plan_save(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    action: str = Form(),
):
    # --- student-build:snippet create_plan_save ---
    # TODO: finish this handler — build the service from db and persist the plan.
    # Thin route: no select()/db.exec() here.
    # The plan being saved is the session draft (degree, minor, typed courses).
    service = _plan_service(db)
    draft = _draft(request)
    service.create_plan(
        user_id=user.id,
        student_name=user.username,
        degree_id=draft.get("degree_id") or 0,
        minor=draft.get("minor") or "",
        courses=draft.get("courses") or [],
        action=action,
        plan_id=draft.get("plan_id"),
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
