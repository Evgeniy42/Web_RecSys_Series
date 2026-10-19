from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.user import UserService
from backend.services.recommendation import RecommendationService

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.get("", response_class=HTMLResponse)
async def recommendation(request: Request, db: Session = Depends(get_db)):
    """Страница рекомендаций"""
    user_service = UserService(db)
    user = user_service.get_current_user(request.session)

    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    recommendation_service = RecommendationService(db)
    recommended_series = recommendation_service.get_for_user(user.id)

    return request.app.state.templates.TemplateResponse(
        request,
        "recommendation/result.html",
        {
            "user": user,
            "recommendations": recommended_series,
            "message": "Рекомендации скоро появятся!",
        }
    )
