from sqlalchemy.orm import Session

from backend.models.series import Series


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: int) -> list[Series]:
        """Персональные рекомендации. ЗАГЛУШКА: здесь будет вызов модели."""
        return []
