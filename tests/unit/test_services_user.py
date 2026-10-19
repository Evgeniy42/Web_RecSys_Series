"""Юнит-тесты для UserService."""

from backend.services.user import UserService


class TestGetById:
    def test_returns_user(self, db_session, sample_user):
        service = UserService(db_session)
        result = service.get_by_id(sample_user.id)
        assert result is not None
        assert result.id == sample_user.id
        assert result.name == "Test User"

    def test_returns_none_for_nonexistent(self, db_session):
        service = UserService(db_session)
        result = service.get_by_id(9999)
        assert result is None


class TestGetByEmail:
    def test_returns_user(self, db_session, sample_user):
        service = UserService(db_session)
        result = service.get_by_email("test@example.com")
        assert result is not None
        assert result.email == "test@example.com"

    def test_returns_none_for_nonexistent(self, db_session):
        service = UserService(db_session)
        result = service.get_by_email("nonexistent@example.com")
        assert result is None


class TestGetCurrentUser:
    def test_returns_user_when_logged_in(self, db_session, sample_user):
        service = UserService(db_session)
        session = {"user_id": sample_user.id}
        result = service.get_current_user(session)
        assert result is not None
        assert result.id == sample_user.id

    def test_returns_none_when_no_user_id(self, db_session):
        service = UserService(db_session)
        result = service.get_current_user({})
        assert result is None

    def test_returns_none_for_nonexistent_user(self, db_session):
        service = UserService(db_session)
        session = {"user_id": 9999}
        result = service.get_current_user(session)
        assert result is None


class TestRegister:
    def test_successful_registration(self, db_session):
        service = UserService(db_session)
        user, error = service.register("New User", "new@example.com", "password123")
        assert user is not None
        assert error is None
        assert user.name == "New User"
        assert user.email == "new@example.com"
        assert user.password != "password123"  # пароль захеширован

    def test_duplicate_email(self, db_session, sample_user):
        service = UserService(db_session)
        user, error = service.register("Another", "test@example.com", "password123")
        assert user is None
        assert error is not None
        assert "уже существует" in error


class TestAuthenticate:
    def test_correct_credentials(self, db_session, sample_user):
        service = UserService(db_session)
        result = service.authenticate("test@example.com", "password123")
        assert result is not None
        assert result.id == sample_user.id

    def test_wrong_password(self, db_session, sample_user):
        service = UserService(db_session)
        result = service.authenticate("test@example.com", "wrongpassword")
        assert result is None

    def test_nonexistent_email(self, db_session):
        service = UserService(db_session)
        result = service.authenticate("nobody@example.com", "password123")
        assert result is None
