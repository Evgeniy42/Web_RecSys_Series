from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.services.series import SeriesService

router = APIRouter(prefix="/series", tags=["series"])


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
    series_service = SeriesService(db)
    context = series_service.search(
        title=title,
        genre_id_raw=genre_id,
        release_year_raw=release_year,
        status=status,
        skip=skip,
        limit=limit,
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "series/list.html",
        context,
    )


@router.get("/{series_id}", response_class=HTMLResponse)
async def series_detail(series_id: int, request: Request, db: Session = Depends(get_db)):
    """Детальная страница сериала"""
    series_service = SeriesService(db)
    user_id = request.session.get("user_id")

    context = series_service.get_detail(series_id, user_id=user_id)

    if not context:
        return request.app.state.templates.TemplateResponse(
            request,
            "series/detail.html",
            {"error": "Сериал не найден"},
            status_code=404,
        )

    return request.app.state.templates.TemplateResponse(
        request,
        "series/detail.html",
        context,
    )
