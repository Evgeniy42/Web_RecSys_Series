from math import ceil
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from backend.models.genre import Genre
from backend.models.series import Series
from backend.repositories.series import SeriesRepository
from backend.repositories.genre import GenreRepository
from backend.repositories.rating import RatingRepository

PAGE_SIZE = 21  # фильмов на одной странице

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
        page: int = 1,
    ) -> dict:
        """Поиск и фильтрация сериалов с пагинацией. Возвращает данные для шаблона."""
        # Пустые строки из формы преобразуем в None, заполненные — в числа
        genre_id = int(genre_id_raw) if genre_id_raw else None
        release_year = int(release_year_raw) if release_year_raw else None
        genre_ids = [genre_id] if genre_id else None

        page = max(page, 1)
        total = self.series_repo.count(
            title=title,
            genre_ids=genre_ids,
            release_year=release_year,
            status=status,
        )
        total_pages = max(ceil(total / PAGE_SIZE), 1)
        # Защита от перехода на страницу за пределами диапазона
        page = min(page, total_pages)

        series_list = self.series_repo.get_all(
            title=title,
            genre_ids=genre_ids,
            release_year=release_year,
            status=status,
            skip=(page - 1) * PAGE_SIZE,
            limit=PAGE_SIZE,
        )
        genres = self.genre_repo.get_all()

        # Строка запроса с активными фильтрами — для ссылок пагинации
        query_params = {}
        if title:
            query_params["title"] = title
        if genre_id:
            query_params["genre_id"] = genre_id
        if release_year:
            query_params["release_year"] = release_year
        if status:
            query_params["status"] = status

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
            "page": page,
            "page_size": PAGE_SIZE,
            "total": total,
            "total_pages": total_pages,
            "page_range": self._page_range(page, total_pages),
            "filters_qs": urlencode(query_params),
        }

    @staticmethod
    def _page_range(page: int, total_pages: int) -> list[int | None]:
        """Номера страниц для пагинации: окно вокруг текущей + края.
        None — разделитель «…»."""
        if total_pages <= 9:
            return list(range(1, total_pages + 1))

        pages: list[int | None] = [1]
        window_start = max(page - 2, 2)
        window_end = min(page + 2, total_pages - 1)

        if window_start > 2:
            pages.append(None)
        pages.extend(range(window_start, window_end + 1))
        if window_end < total_pages - 1:
            pages.append(None)
        pages.append(total_pages)
        return pages

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
