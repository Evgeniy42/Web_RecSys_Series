"""
Standalone-скрипт: загружает пользователей и их оценки из датасета MovieLens
latest-small (`data MovieLens/ratings.csv`) в БД проекта.

Скрипт НЕ является частью приложения — запускается вручную, отдельно
(после импорта фильмов и бэкфилла tmdb_id).

Как связываются данные:
    ratings.csv: userId, movieId, rating(0.5–5.0), timestamp
    movieId -> tmdbId (links.csv) -> series.id (колонка series.tmdb_id)

Пользователи MovieLens — синтетические: почта детерминированная
(ml{userId}@movielens.local — для идемпотентности повторных запусков),
имя и пароль — случайные символы (проект учебный). Пароль хешируется
тем же bcrypt, что и в приложении.

Шкала оценок: в MovieLens 0.5–5.0 с шагом 0.5, в приложении целые 1–10
(CHECK-ограничение таблицы ratings). Значение домножается на 2 —
порядок/похожести при этом не меняются, алгоритм работает одинаково.

Идемпотентен: существующие пользователи и оценки (пара user_id + series_id)
пропускаются.

Запуск (из корня проекта):
    python scripts/import_movielens_ratings.py

Требует: DATABASE_URL (или POSTGRES_*) в `.env`.
"""

import csv
import os
import random
import string
import sys
from pathlib import Path

from dotenv import load_dotenv

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


os.environ["DATABASE_URL"] = get_database_url()

from backend.database import SessionLocal  # noqa: E402
from backend.models.rating import Rating  # noqa: E402
from backend.models.series import Series  # noqa: E402
from backend.models.user import User  # noqa: E402
from backend.utils.security import hash_password  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

ML_EMAIL_DOMAIN = "movielens.local"
CHUNK = 5000  # размер пачки для массовой вставки оценок


def random_string(length: int) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def load_series_by_tmdb(db) -> dict[int, int]:
    """tmdb_id -> series.id"""
    return {
        tmdb_id: sid
        for tmdb_id, sid in db.query(Series.tmdb_id, Series.id).all()
        if tmdb_id is not None
    }


def ml_email(user_id: str) -> str:
    return f"ml{user_id}@{ML_EMAIL_DOMAIN}"


def main() -> None:
    data_dir = PROJECT_ROOT / "data MovieLens"
    db = SessionLocal()

    series_by_tmdb = load_series_by_tmdb(db)
    if not series_by_tmdb:
        sys.exit("Ошибка: не найдено ни одного series.tmdb_id. "
                 "Сначала выполните бэкфилл (scripts/backfill_tmdb_ids.py).")
    print(f"Фильмов с tmdb_id в БД: {len(series_by_tmdb)}")

    # movieId -> tmdbId
    with open(data_dir / "links.csv", newline="", encoding="utf-8") as f:
        tmdb_by_movie = {
            r["movieId"]: r["tmdbId"].strip() for r in csv.DictReader(f)
        }

    # Читаем ratings.csv, сразу мапим на series.id
    rows = []
    unknown_films = 0
    with open(data_dir / "ratings.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tmdb_id = tmdb_by_movie.get(r["movieId"], "").strip()
            series_id = series_by_tmdb.get(int(tmdb_id)) if tmdb_id.isdigit() else None
            if series_id is None:
                unknown_films += 1
                continue
            rows.append((r["userId"], series_id, int(float(r["rating"]) * 2)))

    total_rows = len(rows) + unknown_films
    print(f"Оценок в CSV: {total_rows}, "
          f"привязано к фильмам БД: {len(rows)} "
          f"({len(rows) / total_rows:.1%}), пропущено: {unknown_films}")

    # Пользователи MovieLens (детерминированные email -> идемпотентность)
    ml_user_ids = sorted({r[0] for r in rows}, key=int)
    existing = {
        u.email: u.id
        for u in db.query(User).filter(
            User.email.like(f"%@{ML_EMAIL_DOMAIN}")).all()
    }
    user_id_by_ml = {}
    for ml_uid in ml_user_ids:
        email = ml_email(ml_uid)
        if email in existing:
            user_id_by_ml[ml_uid] = existing[email]
            continue
        user = User(
            email=email,
            name=f"Кинокритик-{random_string(6)}",
            password=hash_password(random_string(16)),
        )
        db.add(user)
        db.flush()
        user_id_by_ml[ml_uid] = user.id
    db.commit()
    print(f"Пользователей MovieLens в БД: {len(user_id_by_ml)} "
          f"(новых создано: {len(ml_user_ids) - len(existing)})")

    # Существующие оценки этих пользователей (для пропуска дубликатов)
    user_db_ids = set(user_id_by_ml.values())
    existing_pairs = set(
        db.query(Rating.user_id, Rating.series_id)
        .filter(Rating.user_id.in_(user_db_ids))
        .all()
    )

    new_ratings = []
    dropped_duplicates = 0
    seen_pairs = set(existing_pairs)
    for ml_uid, series_id, rating in rows:
        # Разные movieId датасета могли сматчиться на одну запись series
        # (например, две версии фильма с одним названием и годом) —
        # такие дубли пары (user_id, series_id) отбрасываем.
        key = (user_id_by_ml[ml_uid], series_id)
        if key in seen_pairs:
            dropped_duplicates += 1
            continue
        seen_pairs.add(key)
        new_ratings.append(Rating(user_id=key[0], series_id=series_id,
                                  rating=rating))
    print(f"Новых оценок к загрузке: {len(new_ratings)} "
          f"(уже было в БД: {len(existing_pairs)}, "
          f"дубли movieId->series: {dropped_duplicates})")

    inserted = 0
    for i in range(0, len(new_ratings), CHUNK):
        db.add_all(new_ratings[i:i + CHUNK])
        try:
            db.commit()
        except IntegrityError:
            # Подстраховка от параллельной записи: добиваем по одной
            db.rollback()
            for rating_obj in new_ratings[i:i + CHUNK]:
                db.add(rating_obj)
                try:
                    db.commit()
                    inserted += 1
                except IntegrityError:
                    db.rollback()
        else:
            inserted += len(new_ratings[i:i + CHUNK])
        print(f"  Загружено: {inserted}/{len(new_ratings)}")

    db.close()
    print(f"\nГотово. Пользователей: {len(user_id_by_ml)}, "
          f"оценок загружено: {inserted}.")


if __name__ == "__main__":
    main()
