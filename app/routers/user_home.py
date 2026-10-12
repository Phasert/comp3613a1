from fastapi import Request
from fastapi.responses import HTMLResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.plan import PlanRepository
from app.services.plan_service import PlanService

from . import router, templates


@router.get("/app", response_class=HTMLResponse, name="user_home_view")
async def user_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = PlanService(PlanRepository(db))
    plan = service.latest_plan_for_user(user.id)
    plan_year = 1
    if plan:
        courses = service.courses_for_plan(plan.plan_id)
        if courses:
            plan_year = min(c.year for c in courses)
    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={
            "user": user,
            "student": service.get_student_for_user(user.id),
            "plan": plan,
            "plan_year": plan_year,
            "nav_create": True,
        },
    )
