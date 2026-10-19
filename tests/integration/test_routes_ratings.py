"""Интеграционные тесты для роутов оценок."""


class TestCreateRating:
    def test_redirects_when_not_logged_in(self, client, seed_series):
        response = client.post(
            "/ratings",
            data={"series_id": seed_series[0].id, "rating": 5, "comment": "Nice"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/auth/login" in response.headers["location"]

    def test_creates_rating(self, auth_client, db_session, seed_series):
        response = auth_client.post(
            "/ratings",
            data={"series_id": seed_series[0].id, "rating": 5, "comment": "Amazing!"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/series/{seed_series[0].id}" in response.headers["location"]

        # Проверяем, что оценка сохранилась
        from backend.models import Rating, User
        u = db_session.query(User).filter_by(email="test@example.com").first()
        rating = db_session.query(Rating).filter_by(user_id=u.id, series_id=seed_series[0].id).first()
        assert rating is not None
        assert rating.rating == 5
        assert rating.comment == "Amazing!"

    def test_rejects_invalid_rating(self, auth_client, seed_series):
        response = auth_client.post(
            "/ratings",
            data={"series_id": seed_series[0].id, "rating": 10, "comment": "Too high"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "invalid_rating" in response.headers["location"]

    def test_rejects_rating_too_low(self, auth_client, seed_series):
        response = auth_client.post(
            "/ratings",
            data={"series_id": seed_series[0].id, "rating": 0},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "invalid_rating" in response.headers["location"]

    def test_upsert_existing_rating(self, auth_client, db_session, seed_series):
        from backend.models import Rating, User

        u = db_session.query(User).filter_by(email="test@example.com").first()

        # Создаём первую оценку
        auth_client.post(
            "/ratings",
            data={"series_id": seed_series[0].id, "rating": 5, "comment": "First"},
            follow_redirects=False,
        )

        # Обновляем через save (тот же эндпоинт)
        auth_client.post(
            "/ratings",
            data={"series_id": seed_series[0].id, "rating": 3, "comment": "Updated"},
            follow_redirects=False,
        )

        ratings = db_session.query(Rating).filter_by(user_id=u.id, series_id=seed_series[0].id).all()
        assert len(ratings) == 1  # still one rating (upsert)
        assert ratings[0].rating == 3
        assert ratings[0].comment == "Updated"


class TestUpdateRating:
    def test_redirects_when_not_logged_in(self, client, db_session, seed_series):
        from backend.models import Rating, User
        from backend.utils.security import hash_password

        user = User(name="Owner", email="owner@example.com", password=hash_password("pass"))
        db_session.add(user)
        db_session.commit()

        rating = Rating(user_id=user.id, series_id=seed_series[0].id, rating=4)
        db_session.add(rating)
        db_session.commit()

        response = client.post(
            f"/ratings/{rating.id}/update",
            data={"series_id": seed_series[0].id, "rating": 2},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/auth/login" in response.headers["location"]

    def test_owner_can_update(self, auth_client, db_session, seed_series):
        from backend.models import Rating, User

        u = db_session.query(User).filter_by(email="test@example.com").first()
        rating = Rating(user_id=u.id, series_id=seed_series[0].id, rating=4, comment="Before")
        db_session.add(rating)
        db_session.commit()

        response = auth_client.post(
            f"/ratings/{rating.id}/update",
            data={"series_id": seed_series[0].id, "rating": 2, "comment": "After"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.refresh(rating)
        assert rating.rating == 2
        assert rating.comment == "After"

    def test_non_owner_cannot_update(self, auth_client, db_session, seed_series):
        from backend.models import Rating, User
        from backend.utils.security import hash_password

        other = User(name="Other", email="other@example.com", password=hash_password("pass"))
        db_session.add(other)
        db_session.commit()

        rating = Rating(user_id=other.id, series_id=seed_series[0].id, rating=4, comment="Original")
        db_session.add(rating)
        db_session.commit()

        response = auth_client.post(
            f"/ratings/{rating.id}/update",
            data={"series_id": seed_series[0].id, "rating": 1, "comment": "Hacked"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.refresh(rating)
        assert rating.rating == 4  # unchanged
        assert rating.comment == "Original"


class TestDeleteRating:
    def test_redirects_when_not_logged_in(self, client, db_session, seed_series):
        from backend.models import Rating, User
        from backend.utils.security import hash_password

        user = User(name="Owner", email="owner@example.com", password=hash_password("pass"))
        db_session.add(user)
        db_session.commit()

        rating = Rating(user_id=user.id, series_id=seed_series[0].id, rating=4)
        db_session.add(rating)
        db_session.commit()

        response = client.post(f"/ratings/{rating.id}/delete", follow_redirects=False)
        assert response.status_code == 303
        assert "/auth/login" in response.headers["location"]

    def test_owner_can_delete(self, auth_client, db_session, seed_series):
        from backend.models import Rating, User

        u = db_session.query(User).filter_by(email="test@example.com").first()
        rating = Rating(user_id=u.id, series_id=seed_series[0].id, rating=4)
        db_session.add(rating)
        db_session.commit()
        rating_id = rating.id

        response = auth_client.post(f"/ratings/{rating_id}/delete", follow_redirects=False)
        assert response.status_code == 303
        assert "/profile" in response.headers["location"]

        assert db_session.query(Rating).filter_by(id=rating_id).first() is None

    def test_non_owner_cannot_delete(self, auth_client, db_session, seed_series):
        from backend.models import Rating, User
        from backend.utils.security import hash_password

        other = User(name="Other", email="other@example.com", password=hash_password("pass"))
        db_session.add(other)
        db_session.commit()

        rating = Rating(user_id=other.id, series_id=seed_series[0].id, rating=4)
        db_session.add(rating)
        db_session.commit()
        rating_id = rating.id

        auth_client.post(f"/ratings/{rating_id}/delete", follow_redirects=False)

        assert db_session.query(Rating).filter_by(id=rating_id).first() is not None
