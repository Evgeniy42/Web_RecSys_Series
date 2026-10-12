from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class Genre(Base):
    __tablename__ = "genres"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    series = relationship("Series", secondary="series_genres", back_populates="genres")
