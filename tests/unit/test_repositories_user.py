"""Юнит-тесты для UserRepository."""

from backend.repositories.user import UserRepository
from backend.utils.security import hash_password


class TestCreate:
    def test_creates_user(self, db_session):
        repo = UserRepository(db_session)
        user = repo.create("Alice", "alice@example.com", hash_password("pass"))
        assert user.id is not None
        assert user.name == "Alice"
        assert user.email == "alice@example.com"

    def test_avatar_url_is_none_by_default(self, db_session):
        repo = UserRepository(db_session)
        user = repo.create("Bob", "bob@example.com", hash_password("pass"))
        assert user.avatar_url is None


class TestGetById:
    def test_returns_user(self, db_session, sample_user):
        repo = UserRepository(db_session)
        user = repo.get_by_id(sample_user.id)
        assert user is not None
        assert user.name == "Test User"

    def test_returns_none(self, db_session):
        repo = UserRepository(db_session)
        assert repo.get_by_id(9999) is None


class TestGetByEmail:
    def test_returns_user(self, db_session, sample_user):
        repo = UserRepository(db_session)
        user = repo.get_by_email("test@example.com")
        assert user is not None

    def test_returns_none(self, db_session):
        repo = UserRepository(db_session)
        assert repo.get_by_email("nobody@example.com") is None


class TestGetAll:
    def test_returns_all(self, db_session, sample_user, sample_user2):
        repo = UserRepository(db_session)
        users = repo.get_all()
        assert len(users) == 2

    def test_respects_limit(self, db_session, sample_user, sample_user2):
        repo = UserRepository(db_session)
        users = repo.get_all(limit=1)
        assert len(users) == 1


class TestUpdate:
    def test_updates_name(self, db_session, sample_user):
        repo = UserRepository(db_session)
        user = repo.update(sample_user.id, name="Updated Name")
        assert user is not None
        assert user.name == "Updated Name"

    def test_updates_avatar_url(self, db_session, sample_user):
        repo = UserRepository(db_session)
        user = repo.update(sample_user.id, avatar_url="/static/images/users_avatars/test.png")
        assert user is not None
        assert user.avatar_url == "/static/images/users_avatars/test.png"

    def test_ignores_unknown_attributes(self, db_session, sample_user):
        repo = UserRepository(db_session)
        user = repo.update(sample_user.id, nonexistent_field="value")
        assert user is not None
        assert not hasattr(user, "nonexistent_field")

    def test_returns_none_for_nonexistent(self, db_session):
        repo = UserRepository(db_session)
        assert repo.update(9999, name="Nobody") is None


class TestDelete:
    def test_deletes_user(self, db_session, sample_user):
        repo = UserRepository(db_session)
        assert repo.delete(sample_user.id) is True
        assert repo.get_by_id(sample_user.id) is None

    def test_returns_false_for_nonexistent(self, db_session):
        repo = UserRepository(db_session)
        assert repo.delete(9999) is False
