"""
Standalone-скрипт импорта фильмов из датасета MovieLens с обогащением
данных через API TMDB (в датасете есть tmdbId для каждого фильма).

Скрипт НЕ является частью приложения — запускается вручную и отдельно
от FastAPI, до или после поднятия БД.

Что делает:
    1. Читает `data MovieLens/movies.csv` и `data MovieLens/links.csv`.
    2. Для каждого фильма с tmdbId запрашивает детали фильма у TMDB
       (/3/movie/{tmdbId}?append_to_response=credits, язык ru-RU,
       с фолбэком на en-US, если описание пустое).
    3. Создаёт записи в таблицах series, genres и series_genres
       (пропускает фильмы, которые уже есть в БД по паре title_en + release_year).

Запуск (из корня проекта):
    python scripts/import_movielens_tmdb.py

Опционально:
    python scripts/import_movielens_tmdb.py --limit 100          # только первые 100
    python scripts/import_movielens_tmdb.py --sleep 0.2          # пауза между запросами, сек
    python scripts/import_movielens_tmdb.py --data-dir "data MovieLens"
    python scripts/import_movielens_tmdb.py --clear            # очистить таблицу
                                                                 # фильмов перед импортом

Флаг --clear удаляет ВСЕ записи из таблицы series (вместе с ними
через ON DELETE CASCADE уходят связи series_genres и оценки ratings),
чтобы не было разногласий в id с тестовыми данными. Без флага скрипт
только дополняет таблицу, пропуская фильмы с совпадающими
title_en + release_year.

Требует переменные окружения (файл `.env` в корне проекта):
    DATABASE_URL  — либо POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB
    TMDB_API_KEY  — ключ API v3 с https://www.themoviedb.org/settings/api
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

# Позволяет запускать скрипт из любой директории: `backend` импортируется
# относительно корня проекта, а не текущей рабочей директории.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    db = os.getenv("POSTGRES_DB", "recsys_series")
    return f"postgresql+psycopg://{user}:{password}@localhost:5432/{db}"


# DATABASE_URL выставляем ДО импорта backend.database: engine создаётся
# в момент импорта и читает переменную окружения один раз.
os.environ["DATABASE_URL"] = get_database_url()

from backend.database import SessionLocal  # noqa: E402
from backend.models.genre import Genre  # noqa: E402
from backend.models.series import Series  # noqa: E402

TMDB_BASE_URL = "https://api.themoviedb.org/3/movie"
TMDB_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
REQUEST_TIMEOUT = 15  # секунд на один запрос к TMDB
MAX_RETRIES = 4  # повторных попыток при 429 / сетевых ошибках


def load_movielens(data_dir: Path) -> list[dict]:
    """Сливает movies.csv и links.csv по movieId -> [{title, year, tmdb_id}]."""
    movies_path = data_dir / "movies.csv"
    links_path = data_dir / "links.csv"

    with open(links_path, newline="", encoding="utf-8") as f:
        tmdb_by_id = {
            row["movieId"]: row["tmdbId"].strip()
            for row in csv.DictReader(f)
        }

    films = []
    with open(movies_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tmdb_id = tmdb_by_id.get(row["movieId"], "").strip()
            if not tmdb_id.isdigit():
                continue
            title, year = split_title(row["title"])
            films.append({
                "title": title,
                "year": year,
                "tmdb_id": int(tmdb_id),
            })
    return films


def split_title(raw_title: str) -> tuple[str, int | None]:
    """'Toy Story (1995)' -> ('Toy Story', 1995); год может отсутствовать."""
    raw_title = raw_title.strip()
    if raw_title.endswith(")") and "(" in raw_title:
        title, _, tail = raw_title.rpartition("(")
        year_str = tail.rstrip(")").strip()
        if year_str.isdigit():
            return title.strip(), int(year_str)
    return raw_title, None


class TmdbClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_movie(self, tmdb_id: int) -> dict | None:
        """Детали фильма. Возвращает None при 404 (фильм удалён из TMDB)."""
        movie = self._request(tmdb_id, language="ru-RU")
        if movie is None:
            return None
        # Если русского описания нет — пробуем оригинальное (en-US)
        if not movie.get("overview"):
            en_movie = self._request(tmdb_id, language="en-US")
            if en_movie:
                movie["overview"] = en_movie.get("overview") or movie.get("overview")
                movie.setdefault("title_en_fallback", en_movie.get("title"))
        return movie

    def _request(self, tmdb_id: int, language: str) -> dict | None:
        url = f"{TMDB_BASE_URL}/{tmdb_id}"
        params = {"api_key": self.api_key, "language": language,
                  "append_to_response": "credits"}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as exc:
                print(f"    [сеть] tmdbId={tmdb_id}: {exc} "
                      f"(попытка {attempt}/{MAX_RETRIES})")
                time.sleep(2 * attempt)
                continue

            if response.status_code == 404:
                return None
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "2"))
                print(f"    [429] tmdbId={tmdb_id}: лимит TMDB, "
                      f"жду {retry_after} сек (попытка {attempt}/{MAX_RETRIES})")
                time.sleep(retry_after)
                continue
            if response.status_code >= 500:
                print(f"    [{response.status_code}] tmdbId={tmdb_id} "
                      f"(попытка {attempt}/{MAX_RETRIES})")
                time.sleep(2 * attempt)
                continue

            response.raise_for_status()
            return response.json()

        print(f"    [пропуск] tmdbId={tmdb_id}: не удалось получить данные")
        return None


def clip(value: str | None, max_len: int) -> str | None:
    """Обрезает строку под размер колонки, чтобы не ловить ошибки БД."""
    if value is None:
        return None
    return value[:max_len]


def build_series(movie: dict, film: dict) -> Series:
    """Маппит ответ TMDB (+ строку из movies.csv) на модель Series."""
    release_date = movie.get("release_date") or ""
    release_year = int(release_date[:4]) if len(release_date) >= 4 else film["year"]

    director = next(
        (c["name"] for c in movie.get("credits", {}).get("crew", [])
         if c.get("job") == "Director"),
        None,
    )
    companies = movie.get("production_companies") or []
    poster_path = movie.get("poster_path")

    return Series(
        title_en=clip(movie.get("title") or film["title"], 255),
        title_original=clip(movie.get("original_title") or film["title"], 255),
        status=clip(movie.get("status") or "Released", 50),
        episode_count=1,  # в датасете MovieLens — полнометражные фильмы
        season_count=1,
        release_year=release_year,
        company=clip(companies[0]["name"] if companies else None, 255),
        director=clip(director, 255),
        poster_url=(f"{TMDB_POSTER_BASE_URL}{poster_path}"
                    if poster_path else None),
        description=clip(movie.get("overview") or None, 2000),
        tmdb_id=film["tmdb_id"],
    )


def get_or_create_genres(db, movie: dict) -> list[Genre]:
    """Жанры TMDB -> строки Genre (по имени, без дубликатов)."""
    genres = []
    for g in movie.get("genres") or []:
        name = clip((g.get("name") or "").strip(), 100)
        if not name:
            continue
        genre = db.query(Genre).filter(Genre.name == name).first()
        if genre is None:
            genre = Genre(name=name)
            db.add(genre)
            db.flush()
        genres.append(genre)
    return genres


def already_exists(db, series: Series) -> bool:
    # Главный ключ идемпотентности — tmdb_id; фолбэк — название + год
    if series.tmdb_id is not None:
        if db.query(Series).filter(Series.tmdb_id == series.tmdb_id).first():
            return True
    query = db.query(Series).filter(Series.title_en == series.title_en)
    if series.release_year:
        query = query.filter(Series.release_year == series.release_year)
    return query.first() is not None


def main() -> None:
    parser = argparse.ArgumentParser(description="Импорт MovieLens + TMDB в БД")
    parser.add_argument("--data-dir", default="data MovieLens",
                        help="Папка с CSV датасета MovieLens")
    parser.add_argument("--limit", type=int, default=None,
                        help="Ограничить количество фильмов (для теста)")
    parser.add_argument("--sleep", type=float, default=0.1,
                        help="Пауза между запросами к TMDB, сек (по умолчанию 0.1)")
    parser.add_argument("--clear", action="store_true",
                        help="Удалить все фильмы из БД перед импортом "
                             "(вместе с ними каскадно удалятся их оценки)")
    args = parser.parse_args()

    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        sys.exit("Ошибка: задайте TMDB_API_KEY в файле .env "
                 "(шаблон — в .env.example)")

    films = load_movielens(PROJECT_ROOT / args.data_dir)
    if args.limit:
        films = films[: args.limit]
    print(f"Фильмов к обработке: {len(films)}")

    client = TmdbClient(api_key)
    db = SessionLocal()

    if args.clear:
        # Массовый DELETE на уровне БД: благодаря ON DELETE CASCADE
        # вместе с фильмами уходят series_genres и ratings.
        deleted = db.query(Series).delete(synchronize_session=False)
        db.commit()
        print(f"Удалено фильмов из БД: {deleted}")

    imported = skipped_exists = skipped_no_tmdb = errors = 0
    try:
        for i, film in enumerate(films, start=1):
            movie = client.get_movie(film["tmdb_id"])
            time.sleep(args.sleep)

            if movie is None:
                skipped_no_tmdb += 1
                continue

            series = build_series(movie, film)
            if already_exists(db, series):
                skipped_exists += 1
                continue

            series.genres = get_or_create_genres(db, movie)
            db.add(series)
            try:
                db.commit()
                imported += 1
            except IntegrityError:
                db.rollback()
                errors += 1

            if i % 100 == 0 or i == len(films):
                print(f"Прогресс: {i}/{len(films)} "
                      f"(импортировано: {imported}, уже в БД: {skipped_exists}, "
                      f"нет в TMDB: {skipped_no_tmdb}, ошибок: {errors})")
    finally:
        db.close()

    print(f"\nГотово. Импортировано: {imported}, "
          f"уже было в БД: {skipped_exists}, не найдено в TMDB: {skipped_no_tmdb}, "
          f"ошибок БД: {errors}")


if __name__ == "__main__":
    main()
