from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend.routes import auth_router, profile_router, series_router, recommendation_router, ratings_router

app = FastAPI()

# Статика
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Шаблоны
templates = Jinja2Templates(directory="frontend/templates")
app.state.templates = templates

# Сессии
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# Роутеры
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(series_router)
app.include_router(recommendation_router)
app.include_router(ratings_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница"""
    return templates.TemplateResponse(
        request,
        "index.html",
    )
