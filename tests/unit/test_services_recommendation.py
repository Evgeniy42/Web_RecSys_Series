"""Юнит-тесты для RecommendationService (заглушка)."""

from backend.services.recommendation import RecommendationService


class TestGetForUser:
    def test_returns_empty_list(self, db_session, sample_user):
        service = RecommendationService(db_session)
        result = service.get_for_user(sample_user.id)
        assert result == []

    def test_returns_empty_list_for_nonexistent_user(self, db_session):
        service = RecommendationService(db_session)
        result = service.get_for_user(9999)
        assert result == []
