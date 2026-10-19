"""Интеграционные тесты для роутов аутентификации."""


class TestRegisterPage:
    def test_get_register_page(self, client):
        response = client.get("/auth/register")
        assert response.status_code == 200
        assert "Регистрация" in response.text


class TestRegisterSubmit:
    def test_successful_registration(self, client):
        response = client.post(
            "/auth/register",
            data={"name": "New User", "email": "new@example.com", "password": "pass123"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/profile"

    def test_duplicate_email_shows_error(self, client, db_session):
        from backend.models import User
        from backend.utils.security import hash_password

        user = User(name="Existing", email="existing@example.com", password=hash_password("pass"))
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/auth/register",
            data={"name": "Another", "email": "existing@example.com", "password": "pass123"},
        )
        assert response.status_code == 200
        assert "уже существует" in response.text


class TestLoginPage:
    def test_get_login_page(self, client):
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert "Вход" in response.text or "Войти" in response.text


class TestLoginSubmit:
    def test_successful_login(self, client, db_session):
        from backend.models import User
        from backend.utils.security import hash_password

        user = User(name="Login User", email="login@example.com", password=hash_password("mypass"))
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/auth/login",
            data={"email": "login@example.com", "password": "mypass"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/profile"

    def test_wrong_password_shows_error(self, client, db_session):
        from backend.models import User
        from backend.utils.security import hash_password

        user = User(name="Login User", email="login@example.com", password=hash_password("mypass"))
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/auth/login",
            data={"email": "login@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 200
        assert "Неверный" in response.text or "неверный" in response.text

    def test_nonexistent_email_shows_error(self, client):
        response = client.post(
            "/auth/login",
            data={"email": "nobody@example.com", "password": "pass123"},
        )
        assert response.status_code == 200
        assert "Неверный" in response.text or "неверный" in response.text


class TestLogout:
    def test_logout_redirects_to_home(self, client):
        response = client.get("/auth/logout", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/"
