from sqlalchemy.orm import Session

from backend.models.rating import Rating


class RatingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, rating_id: int) -> Rating | None:
        return self.db.query(Rating).filter(Rating.id == rating_id).first()

    def get_by_user_and_series(self, user_id: int, series_id: int) -> Rating | None:
        return (
            self.db.query(Rating)
            .filter(Rating.user_id == user_id, Rating.series_id == series_id)
            .first()
        )

    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> list[Rating]:
        return (
            self.db.query(Rating)
            .filter(Rating.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_series(self, series_id: int, skip: int = 0, limit: int = 100) -> list[Rating]:
        return (
            self.db.query(Rating)
            .filter(Rating.series_id == series_id)
            .order_by(Rating.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, user_id: int, series_id: int, rating: int, comment: str | None = None) -> Rating:
        rating_obj = Rating(user_id=user_id, series_id=series_id, rating=rating, comment=comment)
        self.db.add(rating_obj)
        self.db.commit()
        self.db.refresh(rating_obj)
        return rating_obj

    def update(self, rating_id: int, rating: int, comment: str | None = None) -> Rating | None:
        rating_obj = self.get_by_id(rating_id)
        if not rating_obj:
            return None
        rating_obj.rating = rating
        rating_obj.comment = comment
        self.db.commit()
        self.db.refresh(rating_obj)
        return rating_obj

    def delete(self, rating_id: int) -> bool:
        rating_obj = self.get_by_id(rating_id)
        if not rating_obj:
            return False
        self.db.delete(rating_obj)
        self.db.commit()
        return True
