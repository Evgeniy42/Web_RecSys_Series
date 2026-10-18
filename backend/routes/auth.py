from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.user import UserService

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
    user_service = UserService(db)
    user, error = user_service.register(name=name, email=email, password=password)

    if error:
        return request.app.state.templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": error}
        )

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
    user_service = UserService(db)
    user = user_service.authenticate(email=email, password=password)

    if not user:
        return request.app.state.templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Неверный email или пароль"}
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
async def logout(request: Request):
    """Выход"""
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
