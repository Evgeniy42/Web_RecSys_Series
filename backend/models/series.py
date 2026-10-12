from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


series_genres = Table(
    "series_genres",
    Base.metadata,
    Column("series_id", Integer, ForeignKey("series.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True, index=True)
    title_en = Column(String(255), nullable=False)
    title_original = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    episode_count = Column(Integer, nullable=False, default=0)
    season_count = Column(Integer, nullable=False, default=0)
    release_year = Column(Integer, nullable=True)
    company = Column(String(255), nullable=True)
    director = Column(String(255), nullable=True)

    genres = relationship("Genre", secondary=series_genres, back_populates="series")
    ratings = relationship("Rating", back_populates="series", cascade="all, delete-orphan")
