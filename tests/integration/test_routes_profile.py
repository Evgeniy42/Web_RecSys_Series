"""Интеграционные тесты для роутов профиля."""

import io
import os
from unittest.mock import patch


class TestProfilePage:
    def test_redirects_when_not_logged_in(self, client):
        response = client.get("/profile", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/auth/login"

    def test_shows_profile_when_logged_in(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert "Test User" in response.text
        assert "test@example.com" in response.text

    def test_shows_default_avatar_when_no_avatar(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert "unknown.jpg" in response.text

    def test_shows_user_ratings(self, auth_client, db_session, seed_series):
        from backend.models import Rating, User

        u = db_session.query(User).filter_by(email="test@example.com").first()
        rating = Rating(user_id=u.id, series_id=seed_series[0].id, rating=5, comment="Great!")
        db_session.add(rating)
        db_session.commit()

        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert "Breaking Bad" in response.text
        assert "Great!" in response.text


class TestAvatarUpload:
    def test_redirects_when_not_logged_in(self, client):
        # POST без файла возвращает 422 (валидация FastAPI)
        # POST с файлом, но без авторизации возвращает 303 редирект на логин
        files = {"file": ("test.png", io.BytesIO(b"fake"), "image/png")}
        response = client.post("/profile/avatar", files=files, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/auth/login"

    def test_upload_valid_avatar(self, auth_client):
        # Создаём минимальный валидный PNG
        png_data = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        files = {"file": ("avatar.png", io.BytesIO(png_data), "image/png")}

        with patch("backend.routes.profile.AVATARS_DIR", "/tmp/test_avatars"):
            os.makedirs("/tmp/test_avatars", exist_ok=True)
            response = auth_client.post("/profile/avatar", files=files, follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/profile"

        # Проверяем, что avatar_url обновился
        response = auth_client.get("/profile")
        assert "users_avatars/" in response.text
        assert "unknown.jpg" not in response.text

    def test_rejects_invalid_file_type(self, auth_client):
        files = {"file": ("document.txt", io.BytesIO(b"not an image"), "text/plain")}
        response = auth_client.post("/profile/avatar", files=files, follow_redirects=False)
        assert response.status_code == 303
        assert "invalid_file_type" in response.headers["location"]

    def test_rejects_file_too_large(self, auth_client):
        big_data = b"x" * (6 * 1024 * 1024)  # 6 MB
        files = {"file": ("big.png", io.BytesIO(big_data), "image/png")}
        response = auth_client.post("/profile/avatar", files=files, follow_redirects=False)
        assert response.status_code == 303
        assert "file_too_large" in response.headers["location"]
