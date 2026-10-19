"""Юнит-тесты для RatingRepository."""

from backend.repositories.rating import RatingRepository


class TestCreate:
    def test_creates_rating(self, db_session, sample_user, sample_series):
        repo = RatingRepository(db_session)
        rating = repo.create(sample_user.id, sample_series.id, 4, "Nice")
        assert rating.id is not None
        assert rating.rating == 4
        assert rating.comment == "Nice"

    def test_creates_without_comment(self, db_session, sample_user, sample_series):
        repo = RatingRepository(db_session)
        rating = repo.create(sample_user.id, sample_series.id, 3)
        assert rating.comment is None


class TestGetById:
    def test_returns_rating(self, db_session, sample_rating):
        repo = RatingRepository(db_session)
        rating = repo.get_by_id(sample_rating.id)
        assert rating is not None
        assert rating.rating == 5

    def test_returns_none(self, db_session):
        repo = RatingRepository(db_session)
        assert repo.get_by_id(9999) is None


class TestGetByUserAndSeries:
    def test_finds_rating(self, db_session, sample_user, sample_series, sample_rating):
        repo = RatingRepository(db_session)
        rating = repo.get_by_user_and_series(sample_user.id, sample_series.id)
        assert rating is not None
        assert rating.id == sample_rating.id

    def test_returns_none(self, db_session, sample_user, sample_series2):
        repo = RatingRepository(db_session)
        assert repo.get_by_user_and_series(sample_user.id, sample_series2.id) is None


class TestGetByUser:
    def test_returns_ratings(self, db_session, sample_user, sample_rating):
        repo = RatingRepository(db_session)
        ratings = repo.get_by_user(sample_user.id)
        assert len(ratings) == 1

    def test_empty(self, db_session, sample_user2):
        repo = RatingRepository(db_session)
        ratings = repo.get_by_user(sample_user2.id)
        assert len(ratings) == 0


class TestGetBySeries:
    def test_returns_ratings(self, db_session, sample_series, sample_rating):
        repo = RatingRepository(db_session)
        ratings = repo.get_by_series(sample_series.id)
        assert len(ratings) == 1
        assert ratings[0].id == sample_rating.id

    def test_empty(self, db_session, sample_series2):
        repo = RatingRepository(db_session)
        ratings = repo.get_by_series(sample_series2.id)
        assert len(ratings) == 0


class TestUpdate:
    def test_updates_rating(self, db_session, sample_rating):
        repo = RatingRepository(db_session)
        rating = repo.update(sample_rating.id, 2, "Updated comment")
        assert rating is not None
        assert rating.rating == 2
        assert rating.comment == "Updated comment"

    def test_returns_none(self, db_session):
        repo = RatingRepository(db_session)
        assert repo.update(9999, 3) is None


class TestDelete:
    def test_deletes(self, db_session, sample_rating):
        repo = RatingRepository(db_session)
        assert repo.delete(sample_rating.id) is True
        assert repo.get_by_id(sample_rating.id) is None

    def test_returns_false(self, db_session):
        repo = RatingRepository(db_session)
        assert repo.delete(9999) is False
