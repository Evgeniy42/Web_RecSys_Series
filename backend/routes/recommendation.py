from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.user import UserRepository

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.get("", response_class=HTMLResponse)
async def recommendation(request: Request, db: Session = Depends(get_db)):
    """Страница рекомендаций (заглушка)"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    # ЗАГЛУШКА: здесь будет вызов модели рекомендаций
    recommended_series = []

    return request.app.state.templates.TemplateResponse(
        "recommendation/result.html",
        {
            "request": request,
            "user": user,
            "recommendations": recommended_series,
            "message": "Рекомендации скоро появятся!",
        }
    )
