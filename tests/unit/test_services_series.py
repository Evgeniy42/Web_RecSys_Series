"""Юнит-тесты для SeriesService."""

from backend.services.series import SeriesService


class TestSearch:
    def test_returns_all_series(self, db_session, sample_series, sample_series2):
        service = SeriesService(db_session)
        result = service.search(None, None, None, None, 0, 100)
        assert len(result["series_list"]) == 2

    def test_filter_by_title(self, db_session, sample_series, sample_series2):
        service = SeriesService(db_session)
        result = service.search("Breaking", None, None, None, 0, 100)
        assert len(result["series_list"]) == 1
        assert result["series_list"][0].title_en == "Breaking Bad"

    def test_filter_by_title_no_match(self, db_session, sample_series, sample_series2):
        service = SeriesService(db_session)
        result = service.search("NonexistentShow", None, None, None, 0, 100)
        assert len(result["series_list"]) == 0

    def test_filter_by_genre(self, db_session, sample_series, sample_series2, sample_genre):
        service = SeriesService(db_session)
        result = service.search(None, str(sample_genre.id), None, None, 0, 100)
        assert len(result["series_list"]) == 1
        assert result["series_list"][0].title_en == "Breaking Bad"

    def test_filter_by_year(self, db_session, sample_series, sample_series2):
        service = SeriesService(db_session)
        result = service.search(None, None, "2008", None, 0, 100)
        assert len(result["series_list"]) == 1
        assert result["series_list"][0].title_en == "Breaking Bad"

    def test_filter_by_status(self, db_session, sample_series, sample_series2):
        service = SeriesService(db_session)
        result = service.search(None, None, None, "выпускается", 0, 100)
        assert len(result["series_list"]) == 1
        assert result["series_list"][0].title_en == "Stranger Things"

    def test_result_contains_genres_and_statuses(self, db_session, sample_series):
        service = SeriesService(db_session)
        result = service.search(None, None, None, None, 0, 100)
        assert "genres" in result
        assert "status_choices" in result
        assert "filters" in result


class TestGetDetail:
    def test_returns_detail(self, db_session, sample_series, sample_rating):
        service = SeriesService(db_session)
        result = service.get_detail(sample_series.id, sample_rating.user_id)
        assert result is not None
        assert result["series"].id == sample_series.id
        assert result["user_rating"] is not None
        assert len(result["all_ratings"]) == 1

    def test_no_user_rating(self, db_session, sample_series, sample_user2):
        service = SeriesService(db_session)
        result = service.get_detail(sample_series.id, sample_user2.id)
        assert result is not None
        assert result["user_rating"] is None

    def test_nonexistent_series(self, db_session):
        service = SeriesService(db_session)
        result = service.get_detail(9999)
        assert result is None
