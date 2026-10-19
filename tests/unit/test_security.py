"""Юнит-тесты для утилит хеширования паролей."""

from backend.utils.security import hash_password, verify_password


class TestHashPassword:
    def test_returns_string(self):
        result = hash_password("mypassword")
        assert isinstance(result, str)

    def test_produces_different_hashes_for_same_password(self):
        h1 = hash_password("mypassword")
        h2 = hash_password("mypassword")
        assert h1 != h2  # соль bcrypt генерируется случайно

    def test_hash_is_not_plaintext(self):
        result = hash_password("mypassword")
        assert result != "mypassword"
        assert "mypassword" not in result


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_incorrect_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False
