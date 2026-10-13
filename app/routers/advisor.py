from typing import Annotated

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import get_current_user
from app.dependencies.session import SessionDep
from app.models.advisor import Advisor
from app.models.user import User
from app.repositories.advisor import (
    AdvisorRepository,
    QueryReviewRepository,
    ReviewPlanRepository,
)
from app.repositories.plan import PlanRepository
from app.services.advisor_service import DECISIONS, AdvisorService
from app.utilities.flash import flash

from . import router, templates


class AdvisorSession:
    def __init__(self, user: User, advisor: Advisor):
        self.user = user
        self.advisor = advisor


async def advisor_dep(request: Request, db: SessionDep) -> AdvisorSession:
    """Only an account linked to an Advisor row reaches the advisor pages."""
    user = await get_current_user(request, db)
    advisor = AdvisorRepository(db).get_by_user_id(user.id)
    if not advisor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account is not linked to an advisor",
        )
    return AdvisorSession(user, advisor)


AdvisorDep = Annotated[AdvisorSession, Depends(advisor_dep)]


def _service(db) -> AdvisorService:
    return AdvisorService(
        PlanRepository(db),
        AdvisorRepository(db),
        ReviewPlanRepository(db),
        QueryReviewRepository(db),
    )


def _redirect(url):
    return RedirectResponse(url=url, status_code=303)


@router.get("/app/advisor", response_class=HTMLResponse, name="advisor_home_view")
async def advisor_home_view(request: Request, session: AdvisorDep, db: SessionDep):
    service = _service(db)
    queue = service.queue(session.advisor)
    return templates.TemplateResponse(
        request=request,
        name="advisor_home.html",
        context={
            "user": session.user,
            "advisor": session.advisor,
            "queue": queue["rows"],
            "counts": queue["counts"],
            "nav_advisor_home": True,
        },
    )


@router.get("/app/advisor/review/{plan_id}", response_class=HTMLResponse, name="advisor_review_view")
async def advisor_review_view(
    request: Request, session: AdvisorDep, db: SessionDep, plan_id: int
):
    service = _service(db)
    opened = service.open_plan(session.advisor, plan_id)
    if not opened:
        flash(request, "That plan is not in your faculty queue.", "danger")
        return _redirect(str(request.url_for("advisor_home_view")))
    return templates.TemplateResponse(
        request=request,
        name="advisor_review.html",
        context={
            "user": session.user,
            "advisor": session.advisor,
            "opened": opened,
            "decisions": list(DECISIONS),
            "nav_advisor_review": True,
        },
    )


@router.post("/app/advisor/review/{plan_id}", name="advisor_review_save")
async def advisor_review_save(
    request: Request, session: AdvisorDep, db: SessionDep, plan_id: int
):
    # --- student-build:snippet advisor_review_save ---
    # TODO: bind the submitted form, then ask the service to record the
    # per-course decisions and the advisor note. Thin route: no SQL here.
    service = _service(db)
    form = await request.form()
    decisions = {}
    for key, value in form.items():
        if key.startswith("decision_"):
            course_id = int(key[len("decision_") :])
            decisions[course_id] = value
    note = str(form.get("note") or "").strip()
    intent = str(form.get("intent") or "")
    # Submit closes the review; Request Help only stores the decisions so far.
    saved = service.record_review(
        session.advisor, plan_id, decisions, note, intent == "submit"
    )
    if not saved:
        flash(request, "Could not save that review.", "danger")
        return _redirect(str(request.url_for("advisor_review_view", plan_id=plan_id)))
    # --- end snippet ---
    if intent == "help":
        flash(request, "Decisions saved — now ask for the help you need.", "info")
        return _redirect(str(request.url_for("advisor_request_help_view", plan_id=plan_id)))
    flash(request, "Review submitted.", "success")
    return _redirect(str(request.url_for("advisor_home_view")))


@router.get("/app/advisor/review/{plan_id}/help", response_class=HTMLResponse, name="advisor_request_help_view")
async def advisor_request_help_view(
    request: Request, session: AdvisorDep, db: SessionDep, plan_id: int
):
    service = _service(db)
    opened = service.open_plan(session.advisor, plan_id)
    if not opened:
        flash(request, "That plan is not in your faculty queue.", "danger")
        return _redirect(str(request.url_for("advisor_home_view")))
    return templates.TemplateResponse(
        request=request,
        name="advisor_request_help.html",
        context={
            "user": session.user,
            "advisor": session.advisor,
            "opened": opened,
            "faculties": service.all_faculties(),
            "advisers": service.all_advisers(),
            "nav_advisor_review": True,
        },
    )


@router.post("/app/advisor/review/{plan_id}/help", name="advisor_request_help_save")
async def advisor_request_help_save(
    request: Request, session: AdvisorDep, db: SessionDep, plan_id: int
):
    service = _service(db)
    form = await request.form()
    reason = str(form.get("reason") or "").strip()
    faculty = str(form.get("faculty") or session.advisor.faculty)
    staff_id = int(form.get("advisor_staff_id") or session.advisor.staff_id)
    if not reason:
        flash(request, "Add a reason before requesting help.", "danger")
        return _redirect(str(request.url_for("advisor_request_help_view", plan_id=plan_id)))
    query = service.request_help(session.advisor, plan_id, faculty, staff_id, reason)
    if not query:
        flash(request, "Could not open that plan for review.", "danger")
        return _redirect(str(request.url_for("advisor_home_view")))
    asked = service.advisor_repo.get(staff_id)
    flash(
        request,
        f"Help requested from {asked.name if asked else 'another advisor'} — "
        "the plan is now waiting on assistance.",
        "success",
    )
    return _redirect(str(request.url_for("advisor_review_view", plan_id=plan_id)))


@router.get("/app/advisor/query", response_class=HTMLResponse, name="advisor_query_list_view")
async def advisor_query_list_view(request: Request, session: AdvisorDep, db: SessionDep):
    service = _service(db)
    return templates.TemplateResponse(
        request=request,
        name="advisor_query_list.html",
        context={
            "user": session.user,
            "advisor": session.advisor,
            "queries": service.query_rows(session.advisor),
            "nav_advisor_query": True,
        },
    )


@router.get("/app/advisor/assistance/{query_id}", response_class=HTMLResponse, name="advisor_assistance_view")
async def advisor_assistance_view(
    request: Request, session: AdvisorDep, db: SessionDep, query_id: int
):
    service = _service(db)
    help_request = service.assistance(query_id)
    if not help_request:
        flash(request, "That assistance request was not found.", "danger")
        return _redirect(str(request.url_for("advisor_query_list_view")))
    return templates.TemplateResponse(
        request=request,
        name="advisor_assistance.html",
        context={
            "user": session.user,
            "advisor": session.advisor,
            "help": help_request,
            "nav_advisor_query": True,
        },
    )


@router.post("/app/advisor/assistance/{query_id}", name="advisor_assistance_save")
async def advisor_assistance_save(
    request: Request, session: AdvisorDep, db: SessionDep, query_id: int
):
    service = _service(db)
    form = await request.form()
    response = str(form.get("response") or "").strip()
    help_request = service.assistance(query_id)
    if not help_request:
        flash(request, "That assistance request was not found.", "danger")
        return _redirect(str(request.url_for("advisor_query_list_view")))
    if not response:
        flash(request, "Write a response before submitting.", "danger")
        return _redirect(str(request.url_for("advisor_assistance_view", query_id=query_id)))
    service.answer_assistance(query_id, response)
    requester = help_request["requester"]
    flash(
        request,
        f"Response sent to {requester.name if requester else 'the advisor who asked for it'} — "
        "they can now approve or reject the courses and submit their review.",
        "success",
    )
    return _redirect(str(request.url_for("advisor_query_list_view")))