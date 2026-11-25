import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend.routes import auth_router, profile_router, series_router, recommendation_router, ratings_router
from backend.services.backup import BACKUP_INTERVAL_DAYS, run_backup

logger = logging.getLogger(__name__)


async def _backup_loop() -> None:
    """Автоматический бэкап БД.

    Первый запуск — через минуту после старта приложения (проверка
    работоспособности и сразу первая копия), далее — раз в
    BACKUP_INTERVAL_DAYS дней. Учти: каждый рестарт контейнера = ещё один
    бэкап.
    """
    await asyncio.sleep(60)  # дать приложению полностью подняться
    while True:
        try:
            report = await asyncio.to_thread(run_backup)
            if report.ok:
                logger.info("Бэкап выполнен: %s", report)
            else:
                logger.error("Бэкап с ошибками: %s", report)
        except Exception:
            logger.exception("Автоматический бэкап завершился с исключением")
        await asyncio.sleep(BACKUP_INTERVAL_DAYS * 24 * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    backup_task = asyncio.create_task(_backup_loop())
    yield
    backup_task.cancel()


app = FastAPI(lifespan=lifespan)

# Статика
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Шаблоны
templates = Jinja2Templates(directory="frontend/templates")
app.state.templates = templates

# Сессии
SECRET_KEY = os.getenv("SECRET_KEY")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

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
