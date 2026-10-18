from sqlalchemy.orm import Session

from backend.models.rating import Rating
from backend.repositories.rating import RatingRepository

MIN_RATING = 1
MAX_RATING = 5


class RatingService:
    def __init__(self, db: Session):
        self.db = db
        self.rating_repo = RatingRepository(db)

    def is_valid(self, rating: int) -> bool:
        return MIN_RATING <= rating <= MAX_RATING

    def get_by_user(self, user_id: int) -> list[Rating]:
        return self.rating_repo.get_by_user(user_id)

    def save(self, user_id: int, series_id: int, rating: int, comment: str | None = None) -> Rating:
        """Создать или обновить оценку пользователя для сериала."""
        comment_value = comment.strip() if comment else None

        existing = self.rating_repo.get_by_user_and_series(user_id, series_id)
        if existing:
            return self.rating_repo.update(existing.id, rating, comment_value)
        return self.rating_repo.create(user_id=user_id, series_id=series_id, rating=rating, comment=comment_value)

    def update(self, rating_id: int, user_id: int, series_id: int, rating: int, comment: str | None = None) -> bool:
        """Обновить оценку, если она принадлежит пользователю. Возвращает успех."""
        rating_obj = self.rating_repo.get_by_id(rating_id)
        if not rating_obj or rating_obj.user_id != user_id:
            return False

        comment_value = comment.strip() if comment else None
        self.rating_repo.update(rating_id, rating, comment_value)
        return True

    def delete(self, rating_id: int, user_id: int) -> bool:
        """Удалить оценку, если она принадлежит пользователю. Возвращает успех."""
        rating_obj = self.rating_repo.get_by_id(rating_id)
        if not rating_obj or rating_obj.user_id != user_id:
            return False

        self.rating_repo.delete(rating_id)
        return True
