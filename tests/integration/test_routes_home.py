"""Интеграционные тесты для главной страницы."""


class TestHomePage:
    def test_home_page_loads(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_shows_brand(self, client):
        response = client.get("/")
        assert "Rec Сервис" in response.text

    def test_shows_nav_links_for_anonymous(self, client):
        response = client.get("/")
        assert "Войти" in response.text
        assert "Регистрация" in response.text

    def test_shows_nav_links_for_logged_in(self, auth_client):
        response = auth_client.get("/")
        assert "Профиль" in response.text
        assert "Выйти" in response.text
