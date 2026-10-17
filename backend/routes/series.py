from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.repositories.series import SeriesRepository
from backend.repositories.genre import GenreRepository
from backend.repositories.rating import RatingRepository

router = APIRouter(prefix="/series", tags=["series"])

STATUS_CHOICES = [
    ("завершён", "Завершён"),
    ("выпускается", "Выпускается"),
    ("анонс", "Анонс"),
]


@router.get("", response_class=HTMLResponse)
async def series_list(
    request: Request,
    title: Optional[str] = Query(None),
    genre_id: Optional[str] = Query(None),
    release_year: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db),
):
    """Список сериалов с поиском и фильтрацией"""
    series_repo = SeriesRepository(db)
    genre_repo = GenreRepository(db)

    # Пустые строки из формы преобразуем в None, заполненные — в числа
    genre_id_value = int(genre_id) if genre_id else None
    release_year_value = int(release_year) if release_year else None

    series_list = series_repo.get_all(
        title=title,
        genre_ids=[genre_id_value] if genre_id_value else None,
        release_year=release_year_value,
        status=status,
        skip=skip,
        limit=limit,
    )
    genres = genre_repo.get_all()

    return request.app.state.templates.TemplateResponse(
        "series/list.html",
        {
            "request": request,
            "series_list": series_list,
            "genres": genres,
            "status_choices": STATUS_CHOICES,
            "filters": {
                "title": title,
                "genre_id": genre_id_value,
                "release_year": release_year_value,
                "status": status,
            },
        }
    )


@router.get("/{series_id}", response_class=HTMLResponse)
async def series_detail(series_id: int, request: Request, db: Session = Depends(get_db)):
    """Детальная страница сериала"""
    series_repo = SeriesRepository(db)
    series = series_repo.get_by_id(series_id)

    if not series:
        return request.app.state.templates.TemplateResponse(
            "series/detail.html",
            {"request": request, "error": "Сериал не найден"},
            status_code=404,
        )

    user_id = request.session.get("user_id")
    rating_repo = RatingRepository(db)

    user_rating = None
    if user_id:
        user_rating = rating_repo.get_by_user_and_series(user_id, series_id)

    all_ratings = rating_repo.get_by_series(series_id)

    return request.app.state.templates.TemplateResponse(
        "series/detail.html",
        {
            "request": request,
            "series": series,
            "user_rating": user_rating,
            "all_ratings": all_ratings,
        }
    )
