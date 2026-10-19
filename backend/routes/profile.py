import os
import uuid

from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.user import UserService
from backend.services.rating import RatingService

router = APIRouter(prefix="/profile", tags=["profile"])

AVATARS_DIR = "frontend/static/images/users_avatars"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.get("", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    """Страница профиля пользователя"""
    user_service = UserService(db)
    user = user_service.get_current_user(request.session)

    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    rating_service = RatingService(db)
    user_ratings = rating_service.get_by_user(user.id)

    return request.app.state.templates.TemplateResponse(
        request,
        "profile/index.html",
        {
            "user": user,
            "ratings": user_ratings,
        }
    )


@router.post("/avatar", response_class=HTMLResponse)
async def upload_avatar(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Загрузка аватарки пользователя"""
    user_service = UserService(db)
    user = user_service.get_current_user(request.session)

    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return RedirectResponse(url="/profile?error=invalid_file_type", status_code=303)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return RedirectResponse(url="/profile?error=file_too_large", status_code=303)

    os.makedirs(AVATARS_DIR, exist_ok=True)

    # Удаляем старый аватар, если он есть и не является дефолтным
    if user.avatar_url and user.avatar_url != "/static/images/users_avatars/unknown.jpg":
        old_path = os.path.join("frontend/static", user.avatar_url.replace("/static/", "", 1))
        if os.path.exists(old_path):
            os.remove(old_path)

    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(AVATARS_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    avatar_url = f"/static/images/users_avatars/{filename}"
    user_service.user_repo.update(user.id, avatar_url=avatar_url)

    return RedirectResponse(url="/profile", status_code=303)
