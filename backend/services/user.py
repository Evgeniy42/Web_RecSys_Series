from sqlalchemy.orm import Session

from backend.models.user import User
from backend.repositories.user import UserRepository
from backend.utils.security import hash_password, verify_password


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_by_id(self, user_id: int) -> User | None:
        return self.user_repo.get_by_id(user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.user_repo.get_by_email(email)

    def get_current_user(self, session: dict) -> User | None:
        """Получить текущего пользователя из сессии"""
        user_id = session.get("user_id")
        if not user_id:
            return None
        return self.user_repo.get_by_id(user_id)

    def register(self, name: str, email: str, password: str) -> tuple[User | None, str | None]:
        """Регистрация. Возвращает (user, error)."""
        existing = self.user_repo.get_by_email(email)
        if existing:
            return None, "Пользователь с таким email уже существует"

        hashed = hash_password(password)
        user = self.user_repo.create(name=name, email=email, password=hashed)
        return user, None

    def authenticate(self, email: str, password: str) -> User | None:
        """Проверка email/пароля. Возвращает пользователя или None."""
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password):
            return None
        return user
