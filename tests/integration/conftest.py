"""Фикстуры для интеграционных тестов — предоставляет TestClient с переопределённой зависимостью БД."""

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402
from backend.database import Base, get_db  # noqa: E402
from backend.models import Genre, Rating, Series, User  # noqa: E402
from backend.utils.security import hash_password  # noqa: E402


@pytest.fixture(scope="function")
def client():
    """Создаёт TestClient с базой данных SQLite в памяти."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(client):
    """Возвращает сессию базы данных для заполнения тестовыми данными."""
    # Получаем доступ к движку через переопределение зависимостей приложения
    from backend.database import get_db as original_get_db

    # Нужно получить сессию из переопределения
    for dep_override in app.dependency_overrides.values():
        gen = dep_override()
        session = next(gen)
        yield session
        try:
            next(gen)
        except StopIteration:
            pass
        break


@pytest.fixture(scope="function")
def auth_client(client, db_session):
    """Создаёт аутентифицированный TestClient (выполняет вход тестового пользователя)."""
    user = User(
        name="Test User",
        email="test@example.com",
        password=hash_password("password123"),
    )
    db_session.add(user)
    db_session.commit()

    client.post(
        "/auth/login",
        data={"email": "test@example.com", "password": "password123"},
        follow_redirects=False,
    )
    return client


@pytest.fixture(scope="function")
def seed_series(db_session):
    """Заполняет базу данных тестовыми сериалами и жанрами."""
    genre = Genre(name="Drama")
    db_session.add(genre)

    s1 = Series(
        title_en="Breaking Bad",
        title_original="Breaking Bad",
        status="завершён",
        episode_count=62,
        season_count=5,
        release_year=2008,
        company="AMC",
        director="Vince Gilligan",
        poster_url="https://example.com/bb.jpg",
    )
    s1.genres.append(genre)

    s2 = Series(
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

    db_session.add_all([s1, s2])
    db_session.commit()
    return [s1, s2]
