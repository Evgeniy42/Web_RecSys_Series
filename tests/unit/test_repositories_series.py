"""Юнит-тесты для SeriesRepository."""

from backend.repositories.series import SeriesRepository


class TestCreate:
    def test_creates_series(self, db_session, sample_genre):
        repo = SeriesRepository(db_session)
        series = repo.create(
            title_en="Test Show",
            title_original="Test Show",
            status="анонс",
            episode_count=0,
            season_count=1,
            release_year=2025,
            genre_ids=[sample_genre.id],
        )
        assert series.id is not None
        assert series.title_en == "Test Show"
        assert len(series.genres) == 1

    def test_creates_without_genres(self, db_session):
        repo = SeriesRepository(db_session)
        series = repo.create(
            title_en="No Genre Show",
            title_original="No Genre Show",
            status="анонс",
        )
        assert series.id is not None
        assert len(series.genres) == 0


class TestGetById:
    def test_returns_series(self, db_session, sample_series):
        repo = SeriesRepository(db_session)
        series = repo.get_by_id(sample_series.id)
        assert series is not None
        assert series.title_en == "Breaking Bad"

    def test_returns_none(self, db_session):
        repo = SeriesRepository(db_session)
        assert repo.get_by_id(9999) is None


class TestGetAll:
    def test_returns_all(self, db_session, sample_series, sample_series2):
        repo = SeriesRepository(db_session)
        series = repo.get_all()
        assert len(series) == 2

    def test_filter_by_title(self, db_session, sample_series, sample_series2):
        repo = SeriesRepository(db_session)
        series = repo.get_all(title="Stranger")
        assert len(series) == 1
        assert series[0].title_en == "Stranger Things"

    def test_filter_by_year(self, db_session, sample_series, sample_series2):
        repo = SeriesRepository(db_session)
        series = repo.get_all(release_year=2016)
        assert len(series) == 1
        assert series[0].title_en == "Stranger Things"

    def test_filter_by_status(self, db_session, sample_series, sample_series2):
        repo = SeriesRepository(db_session)
        series = repo.get_all(status="завершён")
        assert len(series) == 1
        assert series[0].title_en == "Breaking Bad"

    def test_filter_by_genre(self, db_session, sample_series, sample_series2, sample_genre):
        repo = SeriesRepository(db_session)
        series = repo.get_all(genre_ids=[sample_genre.id])
        assert len(series) == 1
        assert series[0].title_en == "Breaking Bad"


class TestUpdate:
    def test_updates_field(self, db_session, sample_series):
        repo = SeriesRepository(db_session)
        series = repo.update(sample_series.id, title_en="Updated Title")
        assert series is not None
        assert series.title_en == "Updated Title"

    def test_returns_none(self, db_session):
        repo = SeriesRepository(db_session)
        assert repo.update(9999, title_en="Nobody") is None


class TestDelete:
    def test_deletes(self, db_session, sample_series):
        repo = SeriesRepository(db_session)
        assert repo.delete(sample_series.id) is True
        assert repo.get_by_id(sample_series.id) is None

    def test_returns_false(self, db_session):
        repo = SeriesRepository(db_session)
        assert repo.delete(9999) is False
