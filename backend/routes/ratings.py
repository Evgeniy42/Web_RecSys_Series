from fastapi import APIRouter, Depends, Request, Form
from typing import Optional
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.rating import RatingService

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("")
async def create_rating(
    request: Request,
    series_id: int = Form(...),
    rating: int = Form(...),
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Создать или обновить оценку"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    rating_service = RatingService(db)
    if not rating_service.is_valid(rating):
        return RedirectResponse(url=f"/series/{series_id}?error=invalid_rating", status_code=303)

    rating_service.save(user_id=user_id, series_id=series_id, rating=rating, comment=comment)

    return RedirectResponse(url=f"/series/{series_id}", status_code=303)


@router.post("/{rating_id}/update")
async def update_rating(
    rating_id: int,
    request: Request,
    series_id: int = Form(...),
    rating: int = Form(...),
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Обновить оценку и комментарий"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    rating_service = RatingService(db)
    if not rating_service.is_valid(rating):
        return RedirectResponse(url=f"/series/{series_id}?error=invalid_rating", status_code=303)

    rating_service.update(rating_id, user_id=user_id, series_id=series_id, rating=rating, comment=comment)

    return RedirectResponse(url=f"/series/{series_id}", status_code=303)


@router.post("/{rating_id}/delete")
async def delete_rating(rating_id: int, request: Request, db: Session = Depends(get_db)):
    """Удалить оценку"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    rating_service = RatingService(db)
    rating_service.delete(rating_id, user_id=user_id)

    return RedirectResponse(url="/profile", status_code=303)
