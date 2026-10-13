from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.repositories.user import UserRepository
from backend.utils.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    """Страница регистрации"""
    return request.app.state.templates.TemplateResponse(
        "auth/register.html",
        {"request": request}
    )


@router.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Обработка регистрации"""
    user_repo = UserRepository(db)

    # Проверяем, существует ли пользователь
    existing_user = user_repo.get_by_email(email)
    if existing_user:
        return request.app.state.templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": "Пользователь с таким email уже существует"}
        )

    # Создаём пользователя
    hashed_password = hash_password(password)
    user = user_repo.create(name=name, email=email, password=hashed_password)

    # Сохраняем в сессию
    request.session["user_id"] = user.id

    return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    """Страница входа"""
    return request.app.state.templates.TemplateResponse(
        "auth/login.html",
        {"request": request}
    )


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Обработка входа"""
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email)

    if not user or not verify_password(password, user.password):
        return request.app.state.templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Неверный email или пароль"}
        )

    # Сохраняем в сессию
    request.session["user_id"] = user.id

    return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
async def logout(request: Request):
    """Выход"""
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
