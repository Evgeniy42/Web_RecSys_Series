"""Интеграционные тесты для роутов рекомендаций."""


class TestRecommendationPage:
    def test_redirects_when_not_logged_in(self, client):
        response = client.get("/recommendation", follow_redirects=False)
        assert response.status_code == 303
        assert "/auth/login" in response.headers["location"]

    def test_shows_page_when_logged_in(self, auth_client):
        response = auth_client.get("/recommendation")
        assert response.status_code == 200

    def test_shows_stub_message(self, auth_client):
        """Движок рекомендаций — заглушка, должно отображаться соответствующее сообщение."""
        response = auth_client.get("/recommendation")
        assert response.status_code == 200
        # Заглушка возвращает пустой список, поэтому страница должна показать
        # отсутствие рекомендаций или соответствующее сообщение
        assert "Рекомендац" in response.text
