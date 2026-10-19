from sqlalchemy.orm import Session

from backend.models.genre import Genre


class GenreRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, genre_id: int) -> Genre | None:
        return self.db.query(Genre).filter(Genre.id == genre_id).first()

    def get_by_name(self, name: str) -> Genre | None:
        return self.db.query(Genre).filter(Genre.name == name).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Genre]:
        return self.db.query(Genre).offset(skip).limit(limit).all()

    def create(self, name: str) -> Genre:
        genre = Genre(name=name)
        self.db.add(genre)
        self.db.commit()
        self.db.refresh(genre)
        return genre

    def delete(self, genre_id: int) -> bool:
        genre = self.get_by_id(genre_id)
        if not genre:
            return False
        self.db.delete(genre)
        self.db.commit()
        return True
