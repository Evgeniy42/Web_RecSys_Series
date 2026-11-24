"""
Бэкап базы данных: выгрузка pg_dump и отправка на Dropbox и Яндекс Диск.

Работает внутри приложения (вызывается планировщиком раз в 2 недели,
см. lifespan в app.py) — не требует внешнего cron.

Требуемые переменные окружения (.env):
    YANDEX_API_KEY          — OAuth-токен Яндекс Диска
    DROPBOX_ACCESS_TOKEN    — короткоживущий токен Dropbox
    DROPBOX_REFRESH_TOKEN   — refresh-токен Dropbox
Опционально:
    DROPBOX_APP_KEY / DROPBOX_APP_SECRET — нужны, чтобы обновить протухший
        access-токен через refresh-токен (без них при 401 выгрузка в Dropbox
        невозможна)

Тест вручную (из корня проекта):
    python -c "from backend.services.backup import run_backup; print(run_backup())"
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

BACKUP_INTERVAL_DAYS = 14  # периодичность автоматического бэкапа
YANDEX_UPLOAD_URL = "https://cloud-api.yandex.net/v1/disk/resources/upload"
DROPBOX_UPLOAD_URL = "https://content.dropboxapi.com/2/files/upload"
DROPBOX_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
DUMP_TIMEOUT = 600     # секунд на pg_dump
UPLOAD_TIMEOUT = 900   # секунд на загрузку файла
REMOTE_DIR = "/backups/recsys-series"


class BackupError(Exception):
    """Ошибка этапа бэкапа (дамп или конкретная выгрузка)."""


@dataclass
class BackupReport:
    dump_size_mb: float = 0.0
    dropbox: dict = field(default_factory=dict)   # {"ok": bool, "path"/"error"}
    yandex: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.dropbox.get("ok") and self.yandex.get("ok")


# ─── Дамп ─────────────────────────────────────────────────────────────────

def _find_pg_dump() -> str:
    """Путь к pg_dump: переменная окружения, PATH, типичные места."""
    override = os.getenv("BACKUP_PG_DUMP")
    if override:
        return override
    found = shutil.which("pg_dump")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        "/usr/bin/pg_dump",
    ):
        if Path(candidate).exists():
            return candidate
    raise BackupError(
        "pg_dump не найден. Установите PostgreSQL client "
        "или задайте BACKUP_PG_DUMP=/путь/к/pg_dump"
    )


def create_dump(database_url: str, dest: Path) -> Path:
    """pg_dump в custom-формате (-Fc). Возвращает путь к файлу."""
    parsed = urlparse(database_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or ""
    dbname = (parsed.path or "/recsys_series").lstrip("/")

    env = {**os.environ, "PGPASSWORD": password}
    cmd = [
        _find_pg_dump(),
        "-h", host, "-p", str(port), "-U", user,
        "-F", "c", "-f", str(dest), "-d", dbname,
    ]
    result = subprocess.run(cmd, env=env, capture_output=True,
                            text=True, timeout=DUMP_TIMEOUT)
    if result.returncode != 0:
        raise BackupError(f"pg_dump завершился с ошибкой: {result.stderr.strip()}")
    if not dest.exists() or dest.stat().st_size == 0:
        raise BackupError("pg_dump не создал файл дампа")
    return dest


# ─── Dropbox ──────────────────────────────────────────────────────────────

def _dropbox_token() -> str:
    """Access-токен Dropbox.

    У access-токена Dropbox жизнь ~4 часа, а бэкап идёт раз в 2 недели —
    хранённый токен к моменту бэкапа почти наверняка истёк. Поэтому при
    наличии DROPBOX_APP_KEY/DROPBOX_APP_SECRET берём СВЕЖИЙ токен через
    refresh-токен перед каждой выгрузкой. Без app key/secret — используем
    хранённый DROPBOX_ACCESS_TOKEN (с повторной попыткой по 401 ниже).
    """
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    if app_key and app_secret and refresh_token:
        return refresh_dropbox_token()
    return os.getenv("DROPBOX_ACCESS_TOKEN", "")


def refresh_dropbox_token() -> str:
    """Обмен DROPBOX_REFRESH_TOKEN на новый access-токен. Нужны app key/secret."""
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    if not (app_key and app_secret and refresh_token):
        raise BackupError(
            "Access-токен Dropbox истёк, а DROPBOX_APP_KEY/DROPBOX_APP_SECRET "
            "не заданы — обновить токен невозможно. Добавьте их в .env."
        )
    resp = requests.post(
        DROPBOX_TOKEN_URL,
        data={"grant_type": "refresh_token",
              "refresh_token": refresh_token},
        auth=(app_key, app_secret), timeout=30,
    )
    if resp.status_code != 200:
        raise BackupError(f"Обновление токена Dropbox: HTTP {resp.status_code}: "
                          f"{resp.text[:300]}")
    token = resp.json()["access_token"]
    os.environ["DROPBOX_ACCESS_TOKEN"] = token  # для последующих выгрузок в этом процессе
    logger.info("Dropbox access-токен обновлён через refresh-токен")
    return token


def upload_to_dropbox(file_path: Path, remote_name: str) -> str:
    """Загрузка файла в Dropbox. Возвращает путь в облаке."""
    remote_path = f"{REMOTE_DIR}/{remote_name}"
    arg = json.dumps({"path": remote_path, "mode": "overwrite",
                      "autorename": False})

    def _post(token: str) -> requests.Response:
        with open(file_path, "rb") as f:
            return requests.post(
                DROPBOX_UPLOAD_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Dropbox-API-Arg": arg,
                    "Content-Type": "application/octet-stream",
                },
                data=f, timeout=UPLOAD_TIMEOUT,
            )

    try:
        resp = _post(_dropbox_token())
    except BackupError:
        # Не удалось обновить токен заранее — пробуем хранённый access-токен
        resp = _post(os.getenv("DROPBOX_ACCESS_TOKEN", ""))
    if resp.status_code == 401 and os.getenv("DROPBOX_REFRESH_TOKEN"):
        resp = _post(refresh_dropbox_token())
    if resp.status_code != 200:
        raise BackupError(f"Dropbox: HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json().get("path_display", remote_path)


# ─── Яндекс Диск ──────────────────────────────────────────────────────────

def _ensure_yandex_dir(remote_dir: str, token: str) -> None:
    """Создание папки на Яндекс Диске по сегментам — API не создаёт
    вложенные папки одним вызовом. 409 «папка уже существует» — ок."""
    segments = remote_dir.strip("/").split("/")
    path = ""
    for seg in segments:
        path = f"{path}/{seg}"
        resp = requests.put(
            "https://cloud-api.yandex.net/v1/disk/resources",
            params={"path": path},
            headers={"Authorization": f"OAuth {token}"}, timeout=30,
        )
        already = (resp.status_code == 409
                   and "ExistedDirectory" in resp.text)
        if resp.status_code != 201 and not already:
            raise BackupError(f"Яндекс Диск (создание папки {path}): "
                              f"HTTP {resp.status_code}: {resp.text[:300]}")


def upload_to_yandex(file_path: Path, remote_name: str, token: str) -> str:
    """Загрузка файла на Яндекс Диск: создать папку -> href -> PUT."""
    _ensure_yandex_dir(REMOTE_DIR, token)
    remote_path = f"{REMOTE_DIR}/{remote_name}"
    resp = requests.get(
        YANDEX_UPLOAD_URL,
        params={"path": remote_path, "overwrite": "true"},
        headers={"Authorization": f"OAuth {token}"}, timeout=30,
    )
    if resp.status_code != 200:
        raise BackupError(f"Яндекс Диск (получение ссылки): "
                          f"HTTP {resp.status_code}: {resp.text[:300]}")
    href = resp.json()["href"]
    with open(file_path, "rb") as f:
        put = requests.put(href, data=f, timeout=UPLOAD_TIMEOUT)
    if put.status_code not in (200, 201):
        raise BackupError(f"Яндекс Диск (загрузка): "
                          f"HTTP {put.status_code}: {put.text[:300]}")
    return remote_path


# ─── Общий запуск ─────────────────────────────────────────────────────────

def run_backup(database_url: str | None = None) -> BackupReport:
    """Дамп -> Dropbox + Яндекс. Одна выгрузка падает — вторая всё равно работает."""
    database_url = database_url or os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}"
        f":{os.getenv('POSTGRES_PASSWORD', '')}"
        f"@localhost:5432/{os.getenv('POSTGRES_DB', 'recsys_series')}",
    )
    yandex_key = os.getenv("YANDEX_API_KEY", "")
    report = BackupReport()
    name = f"recsys_{datetime.now():%Y%m%d_%H%M%S}.dump"

    tmp_dir = Path(tempfile.mkdtemp(prefix="recsys_backup_"))
    dump_path = tmp_dir / name
    try:
        create_dump(database_url, dump_path)
        report.dump_size_mb = round(dump_path.stat().st_size / 1024 / 1024, 2)
        logger.info("Дамп создан: %s (%.2f МБ)", dump_path,
                    report.dump_size_mb)

        if yandex_key:
            try:
                path = upload_to_yandex(dump_path, name, yandex_key)
                report.yandex = {"ok": True, "path": path}
            except BackupError as exc:
                logger.error("Яндекс Диск: %s", exc)
                report.yandex = {"ok": False, "error": str(exc)}
        else:
            report.yandex = {"ok": False, "error": "YANDEX_API_KEY не задан"}

        try:
            path = upload_to_dropbox(dump_path, name)
            report.dropbox = {"ok": True, "path": path}
        except BackupError as exc:
            logger.error("Dropbox: %s", exc)
            report.dropbox = {"ok": False, "error": str(exc)}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return report
