import threading

import pandas as pd
from sqlalchemy.orm import Session

from backend.models.rating import Rating
from backend.models.series import Series
from backend.services.recommendation_engine import ItemItemKNN


class RecommendationService:
    """Персональные рекомендации на item-item kNN.

    Модель кешируется в памяти процесса и пересобирается только когда
    изменилось число оценок в БД (полный пересчёт на этом датасете — секунды).
    """

    _cache: dict = {"ratings_count": None, "model": None}
    _lock = threading.Lock()

    def __init__(self, db: Session):
        self.db = db

    def _get_model(self) -> ItemItemKNN | None:
        ratings_count = self.db.query(Rating).count()
        with self._lock:
            if (self._cache["ratings_count"] == ratings_count
                    and self._cache["model"] is not None):
                return self._cache["model"]

            rows = self.db.query(
                Rating.user_id, Rating.series_id, Rating.rating).all()
            if not rows:
                self._cache.update(ratings_count=ratings_count, model=None)
                return None

            df = pd.DataFrame(rows, columns=["user_id", "series_id", "rating"])
            model = ItemItemKNN(df)
            self._cache.update(ratings_count=ratings_count, model=model)
            return model

    def get_for_user(self, user_id: int, n: int = 10) -> list[Series]:
        """Топ-N рекомендованных фильмов (в порядке убывания скора)."""
        model = self._get_model()
        if model is None:
            return []

        series_ids = model.recommend(user_id, n=n)
        if not series_ids:
            return []

        series = self.db.query(Series).filter(Series.id.in_(series_ids)).all()
        order = {sid: i for i, sid in enumerate(series_ids)}
        return sorted(series, key=lambda s: order[s.id])
