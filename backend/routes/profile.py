from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.user import UserService
from backend.services.rating import RatingService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    """Страница профиля пользователя"""
    user_service = UserService(db)
    user = user_service.get_current_user(request.session)

    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    rating_service = RatingService(db)
    user_ratings = rating_service.get_by_user(user.id)

    return request.app.state.templates.TemplateResponse(
        "profile/index.html",
        {
            "request": request,
            "user": user,
            "ratings": user_ratings,
        }
    )
