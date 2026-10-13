from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.rating import RatingRepository
from backend.repositories.user import UserRepository

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("")
async def create_rating(
    request: Request,
    series_id: int = Form(...),
    rating: int = Form(...),
    db: Session = Depends(get_db),
):
    """Создать или обновить оценку"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    # Валидация рейтинга
    if rating < 1 or rating > 10:
        return RedirectResponse(url=f"/series/{series_id}?error=invalid_rating", status_code=303)

    rating_repo = RatingRepository(db)

    # Проверяем, есть ли уже оценка
    existing = rating_repo.get_by_user_and_series(user_id, series_id)
    if existing:
        rating_repo.update(existing.id, rating)
    else:
        rating_repo.create(user_id=user_id, series_id=series_id, rating=rating)

    return RedirectResponse(url=f"/series/{series_id}", status_code=303)


@router.post("/{rating_id}/delete")
async def delete_rating(rating_id: int, request: Request, db: Session = Depends(get_db)):
    """Удалить оценку"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    rating_repo = RatingRepository(db)
    rating = rating_repo.get_by_id(rating_id)

    if not rating or rating.user_id != user_id:
        return RedirectResponse(url="/profile", status_code=303)

    rating_repo.delete(rating_id)
    return RedirectResponse(url="/profile", status_code=303)
