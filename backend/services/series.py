from sqlalchemy.orm import Session

from backend.models.genre import Genre
from backend.models.series import Series
from backend.repositories.series import SeriesRepository
from backend.repositories.genre import GenreRepository
from backend.repositories.rating import RatingRepository

STATUS_CHOICES = [
    ("завершён", "Завершён"),
    ("выпускается", "Выпускается"),
    ("анонс", "Анонс"),
]


class SeriesService:
    def __init__(self, db: Session):
        self.db = db
        self.series_repo = SeriesRepository(db)
        self.genre_repo = GenreRepository(db)
        self.rating_repo = RatingRepository(db)

    def search(
        self,
        title: str | None = None,
        genre_id_raw: str | None = None,
        release_year_raw: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> dict:
        """Поиск и фильтрация сериалов. Возвращает данные для шаблона."""
        # Пустые строки из формы преобразуем в None, заполненные — в числа
        genre_id = int(genre_id_raw) if genre_id_raw else None
        release_year = int(release_year_raw) if release_year_raw else None

        series_list = self.series_repo.get_all(
            title=title,
            genre_ids=[genre_id] if genre_id else None,
            release_year=release_year,
            status=status,
            skip=skip,
            limit=limit,
        )
        genres = self.genre_repo.get_all()

        return {
            "series_list": series_list,
            "genres": genres,
            "status_choices": STATUS_CHOICES,
            "filters": {
                "title": title,
                "genre_id": genre_id,
                "release_year": release_year,
                "status": status,
            },
        }

    def get_detail(self, series_id: int, user_id: int | None = None) -> dict | None:
        """Детали сериала с оценками. Возвращает None, если не найден."""
        series = self.series_repo.get_by_id(series_id)
        if not series:
            return None

        user_rating = None
        if user_id:
            user_rating = self.rating_repo.get_by_user_and_series(user_id, series_id)

        all_ratings = self.rating_repo.get_by_series(series_id)

        return {
            "series": series,
            "user_rating": user_rating,
            "all_ratings": all_ratings,
        }
