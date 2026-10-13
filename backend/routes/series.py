from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.repositories.series import SeriesRepository
from backend.repositories.genre import GenreRepository

router = APIRouter(prefix="/series", tags=["series"])


@router.get("", response_class=HTMLResponse)
async def series_list(
    request: Request,
    genre_id: Optional[int] = Query(None),
    release_year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db),
):
    """Список сериалов с фильтрацией"""
    series_repo = SeriesRepository(db)
    genre_repo = GenreRepository(db)

    series_list = series_repo.get_all(
        genre_ids=[genre_id] if genre_id else None,
        release_year=release_year,
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
            "filters": {
                "genre_id": genre_id,
                "release_year": release_year,
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

    return request.app.state.templates.TemplateResponse(
        "series/detail.html",
        {"request": request, "series": series}
    )
