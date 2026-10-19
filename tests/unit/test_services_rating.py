"""Юнит-тесты для RatingService."""

from backend.services.rating import RatingService


class TestIsValid:
    def test_valid_ratings(self, db_session):
        service = RatingService(db_session)
        for r in range(1, 6):
            assert service.is_valid(r) is True

    def test_too_low(self, db_session):
        service = RatingService(db_session)
        assert service.is_valid(0) is False
        assert service.is_valid(-1) is False

    def test_too_high(self, db_session):
        service = RatingService(db_session)
        assert service.is_valid(6) is False
        assert service.is_valid(10) is False

    def test_float_in_range(self, db_session):
        service = RatingService(db_session)
        # is_valid использует сравнение <=, поэтому 3.5 формально "валиден" в текущей реализации
        assert service.is_valid(3.5) is True


class TestGetByUser:
    def test_returns_user_ratings(self, db_session, sample_user, sample_rating):
        service = RatingService(db_session)
        ratings = service.get_by_user(sample_user.id)
        assert len(ratings) == 1
        assert ratings[0].id == sample_rating.id

    def test_empty_when_no_ratings(self, db_session, sample_user2):
        service = RatingService(db_session)
        ratings = service.get_by_user(sample_user2.id)
        assert len(ratings) == 0


class TestSave:
    def test_create_new_rating(self, db_session, sample_user, sample_series2):
        service = RatingService(db_session)
        rating = service.save(sample_user.id, sample_series2.id, 4, "Good show")
        assert rating.id is not None
        assert rating.rating == 4
        assert rating.comment == "Good show"

    def test_update_existing_rating(self, db_session, sample_user, sample_series, sample_rating):
        service = RatingService(db_session)
        rating = service.save(sample_user.id, sample_series.id, 3, "Changed my mind")
        assert rating.id == sample_rating.id  # та же запись обновлена
        assert rating.rating == 3
        assert rating.comment == "Changed my mind"

    def test_save_without_comment(self, db_session, sample_user, sample_series2):
        service = RatingService(db_session)
        rating = service.save(sample_user.id, sample_series2.id, 5)
        assert rating.comment is None


class TestUpdate:
    def test_successful_update(self, db_session, sample_user, sample_series, sample_rating):
        service = RatingService(db_session)
        result = service.update(sample_rating.id, sample_user.id, sample_series.id, 2, "Not great")
        assert result is True
        db_session.refresh(sample_rating)
        assert sample_rating.rating == 2
        assert sample_rating.comment == "Not great"

    def test_wrong_user_cannot_update(self, db_session, sample_user2, sample_series, sample_rating):
        service = RatingService(db_session)
        result = service.update(sample_rating.id, sample_user2.id, sample_series.id, 1, "Hacked")
        assert result is False
        db_session.refresh(sample_rating)
        assert sample_rating.rating == 5  # без изменений

    def test_nonexistent_rating(self, db_session, sample_user, sample_series):
        service = RatingService(db_session)
        result = service.update(9999, sample_user.id, sample_series.id, 3)
        assert result is False


class TestDelete:
    def test_successful_delete(self, db_session, sample_user, sample_rating):
        service = RatingService(db_session)
        result = service.delete(sample_rating.id, sample_user.id)
        assert result is True
        assert service.get_by_user(sample_user.id) == []

    def test_wrong_user_cannot_delete(self, db_session, sample_user2, sample_rating):
        service = RatingService(db_session)
        result = service.delete(sample_rating.id, sample_user2.id)
        assert result is False

    def test_nonexistent_rating(self, db_session, sample_user):
        service = RatingService(db_session)
        result = service.delete(9999, sample_user.id)
        assert result is False
