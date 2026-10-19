import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Убедимся, что корень проекта есть в sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.database import Base, get_db  # noqa: E402
from backend.models import Genre, Rating, Series, User  # noqa: E402
from backend.utils.security import hash_password  # noqa: E402


@pytest.fixture(scope="function")
def db_engine():
    """Создаёт новую базу данных SQLite в памяти для каждого теста."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Создаёт новую сессию базы данных для каждого теста."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def sample_user(db_session):
    """Создаёт тестового пользователя."""
    user = User(
        name="Test User",
        email="test@example.com",
        password=hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_user2(db_session):
    """Создаёт второго тестового пользователя."""
    user = User(
        name="Second User",
        email="second@example.com",
        password=hash_password("password456"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_genre(db_session):
    """Создаёт тестовый жанр."""
    genre = Genre(name="Drama")
    db_session.add(genre)
    db_session.commit()
    db_session.refresh(genre)
    return genre


@pytest.fixture(scope="function")
def sample_series(db_session, sample_genre):
    """Создаёт тестовый сериал."""
    series = Series(
        title_en="Breaking Bad",
        title_original="Breaking Bad",
        status="завершён",
        episode_count=62,
        season_count=5,
        release_year=2008,
        company="AMC",
        director="Vince Gilligan",
        poster_url="https://example.com/poster.jpg",
    )
    series.genres.append(sample_genre)
    db_session.add(series)
    db_session.commit()
    db_session.refresh(series)
    return series


@pytest.fixture(scope="function")
def sample_series2(db_session):
    """Создаёт второй тестовый сериал (без жанра)."""
    series = Series(
        title_en="Stranger Things",
        title_original="Stranger Things",
        status="выпускается",
        episode_count=42,
        season_count=4,
        release_year=2016,
        company="Netflix",
        director="Duffer Brothers",
        poster_url=None,
    )
    db_session.add(series)
    db_session.commit()
    db_session.refresh(series)
    return series


@pytest.fixture(scope="function")
def sample_rating(db_session, sample_user, sample_series):
    """Создаёт тестовую оценку."""
    rating = Rating(
        user_id=sample_user.id,
        series_id=sample_series.id,
        rating=5,
        comment="Amazing show!",
    )
    db_session.add(rating)
    db_session.commit()
    db_session.refresh(rating)
    return rating
