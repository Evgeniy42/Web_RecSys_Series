from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.user import UserRepository
from backend.repositories.rating import RatingRepository

router = APIRouter(prefix="/profile", tags=["profile"])


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Получить текущего пользователя из сессии"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user_repo = UserRepository(db)
    return user_repo.get_by_id(user_id)


@router.get("", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    """Страница профиля пользователя"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    rating_repo = RatingRepository(db)
    user_ratings = rating_repo.get_by_user(user.id)

    return request.app.state.templates.TemplateResponse(
        "profile/index.html",
        {
            "request": request,
            "user": user,
            "ratings": user_ratings,
        }
    )
