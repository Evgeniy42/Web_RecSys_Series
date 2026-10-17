from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.models.series import Series, series_genres


class SeriesRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, series_id: int) -> Series | None:
        return self.db.query(Series).filter(Series.id == series_id).first()

    def get_all(
        self,
        title: str | None = None,
        genre_ids: list[int] | None = None,
        release_year: int | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Series]:
        query = self.db.query(Series)

        if title:
            pattern = f"%{title.strip()}%"
            query = query.filter(
                or_(
                    Series.title_en.ilike(pattern),
                    Series.title_original.ilike(pattern),
                )
            )
        if genre_ids:
            query = query.join(series_genres).filter(series_genres.c.genre_id.in_(genre_ids))
        if release_year:
            query = query.filter(Series.release_year == release_year)
        if status:
            query = query.filter(Series.status == status)

        return query.distinct().offset(skip).limit(limit).all()

    def create(
        self,
        title_en: str,
        title_original: str,
        status: str,
        episode_count: int = 0,
        season_count: int = 0,
        release_year: int | None = None,
        company: str | None = None,
        director: str | None = None,
        poster_url: str | None = None,
        genre_ids: list[int] | None = None,
    ) -> Series:

        series = Series(
            title_en=title_en,
            title_original=title_original,
            status=status,
            episode_count=episode_count,
            season_count=season_count,
            release_year=release_year,
            company=company,
            director=director,
            poster_url=poster_url
        )

        if genre_ids:
            from backend.models.genre import Genre
            genres = self.db.query(Genre).filter(Genre.id.in_(genre_ids)).all()
            series.genres = genres

        self.db.add(series)
        self.db.commit()
        self.db.refresh(series)
        return series

    def update(self, series_id: int, **kwargs) -> Series | None:
        series = self.get_by_id(series_id)
        if not series:
            return None
        for key, value in kwargs.items():
            if hasattr(series, key):
                setattr(series, key, value)
        self.db.commit()
        self.db.refresh(series)
        return series

    def delete(self, series_id: int) -> bool:
        series = self.get_by_id(series_id)
        if not series:
            return False
        self.db.delete(series)
        self.db.commit()
        return True
