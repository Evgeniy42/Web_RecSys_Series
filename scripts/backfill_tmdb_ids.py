"""
Standalone-разовый скрипт: заполняет колонку series.tmdb_id для фильмов,
загруженных ДО появления этой колонки.

Логика:
    1. movieId (MovieLens) -> tmdbId — из `data MovieLens/links.csv`.
    2. Фильм из movies.csv сопоставляется со строкой series по нормализованному
       title_original + году (MovieLens даёт английское название и часто
       оригинал в скобках, у TMDB в title_original — оригинальное название).
    3. Что не сматчилось строками — добивается через эндпоинт TMDB
       /movie/{tmdbId}/alternative_titles (там лежат английские тайтлы).

Запуск (из корня проекта):
    python scripts/backfill_tmdb_ids.py

Требует: DATABASE_URL (или POSTGRES_*) и TMDB_API_KEY в `.env`.
Идемпотентен: повторный прогон только достраивает незаполненное.
"""

import csv
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

import psycopg  # noqa: E402

TMDB_ALT_TITLES_URL = "https://api.themoviedb.org/3/movie/{tmdb_id}/alternative_titles"
REQUEST_TIMEOUT = 15
SLEEP = 0.1  # пауза между запросами к TMDB


# ─── Нормализация названий ────────────────────────────────────────────────

def normalize(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[''`]", "", t)
    # "American President, The" -> "the american president" (ДО удаления пунктуации)
    for art in (", the", ", a", ", an", ", les", ", le", ", la", ", il", ", l"):
        if t.endswith(art):
            t = art[2:] + " " + t[: -len(art)]
            break
    t = re.sub(r"[^a-z0-9а-яё ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def split_year(raw: str) -> tuple[str, int | None]:
    """Отрезает хвостовые '(год)' и возвращает (название_без_года, год)."""
    if raw.endswith(")") and "(" in raw:
        i = raw.rindex("(")
        tail = raw[i + 1:-1].strip()
        if tail.isdigit():
            return raw[:i].strip(), int(tail)
    return raw.strip(), None


def ml_title_variants(base: str) -> list[str]:
    """Основное название + все скобочные части (оригиналы, a.k.a.)."""
    variants = []
    main = re.split(r"\(", base)[0].strip()
    if main:
        variants.append(main)
    for part in re.findall(r"\(([^)]+)\)", base):
        part = re.sub(r"^a\.k\.a\.\s*", "", part).strip()
        if part:
            variants.append(part)
    if not variants:
        variants.append(base)

    seen, out = set(), []
    for v in variants:
        n = normalize(v)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


# ─── Загрузка данных ──────────────────────────────────────────────────────

def load_links(data_dir: Path) -> dict[str, str]:
    with open(data_dir / "links.csv", newline="", encoding="utf-8") as f:
        return {r["movieId"]: r["tmdbId"].strip() for r in csv.DictReader(f)}


def build_series_index(conn) -> tuple[dict, dict]:
    """Индексы: (норм. название, год) -> [id], норм. название -> [id]."""
    cur = conn.cursor()
    cur.execute("SELECT id, title_original, release_year FROM series")
    by_key: dict[tuple[str, int | None], list[int]] = defaultdict(list)
    by_title: dict[str, list[int]] = defaultdict(list)
    for sid, title_original, year in cur.fetchall():
        n = normalize(title_original or "")
        if not n:
            continue
        by_key[(n, year)].append(sid)
        by_title[n].append(sid)
    return by_key, by_title


def match_variants(variants, year, by_key, by_title) -> int | None:
    """Уникальный матч по (название, год); фолбэк — по названию без года,
    только если оно уникально в БД."""
    for v in variants:
        cands = by_key.get((v, year), [])
        if cands:
            return cands[0]
    for v in variants:
        cands = by_title.get(v, [])
        if len(cands) == 1:
            return cands[0]
    return None


def fetch_alt_titles(api_key: str, tmdb_id: str) -> list[str]:
    try:
        r = requests.get(TMDB_ALT_TITLES_URL.format(tmdb_id=tmdb_id),
                         params={"api_key": api_key}, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return []
        return [t["title"] for t in r.json().get("titles", []) if t.get("title")]
    except requests.RequestException:
        return []


def main() -> None:
    data_dir = PROJECT_ROOT / "data MovieLens"
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        sys.exit("Ошибка: задайте TMDB_API_KEY в файле .env")

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # SQLAlchemy-строка (postgresql+psycopg://) -> обычный DSN для psycopg
        database_url = database_url.replace("postgresql+psycopg://", "postgresql://")
        database_url = database_url.split("?")[0]
    if not database_url:
        database_url = (
            f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}"
            f":{os.getenv('POSTGRES_PASSWORD', '')}"
            f"@localhost:5432/{os.getenv('POSTGRES_DB', 'recsys_series')}"
        )

    conn = psycopg.connect(database_url)
    by_key, by_title = build_series_index(conn)
    links = load_links(data_dir)

    # movieId -> (tmdbId, варианты названия, год)
    films = []
    with open(data_dir / "movies.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tmdb_id = links.get(row["movieId"], "").strip()
            if not tmdb_id.isdigit():
                continue
            base, year = split_year(row["title"].strip())
            films.append({
                "movieId": row["movieId"],
                "tmdb_id": int(tmdb_id),
                "variants": ml_title_variants(base),
                "year": year,
            })
    print(f"Фильмов в датасете с tmdbId: {len(films)}")

    updates: dict[int, int] = {}  # series_id -> tmdb_id
    need_api: list[dict] = []

    for film in films:
        sid = match_variants(film["variants"], film["year"], by_key, by_title)
        if sid is not None:
            updates[sid] = film["tmdb_id"]
        else:
            need_api.append(film)

    print(f"Сматчено по названию: {len(updates)}, осталось: {len(need_api)}")

    # Добиваем через alternative_titles TMDB
    for i, film in enumerate(need_api, start=1):
        alt = fetch_alt_titles(api_key, film["tmdb_id"])
        time.sleep(SLEEP)
        variants = film["variants"] + [normalize(a) for a in alt]
        sid = match_variants(variants, film["year"], by_key, by_title)
        if sid is not None:
            updates[sid] = film["tmdb_id"]
        if i % 100 == 0 or i == len(need_api):
            print(f"  TMDB-подбор: {i}/{len(need_api)}, "
                  f"досматчено: {len(updates)}")

    # Применяем к БД (одним сериалом может владеть один tmdb_id — unique)
    cur = conn.cursor()
    applied = skipped_conflict = 0
    for sid, tmdb_id in updates.items():
        try:
            cur.execute("UPDATE series SET tmdb_id = %s WHERE id = %s",
                        (tmdb_id, sid))
            applied += 1
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            skipped_conflict += 1
    conn.commit()
    conn.close()

    total_film_rows = len(films)
    print(f"\nГотово. UPDATE выполнен: {applied} "
          f"(конфликтов уникальности: {skipped_conflict}).")
    print(f"Покрытие датасета: {applied}/{total_film_rows} "
          f"= {applied / total_film_rows:.1%}")


if __name__ == "__main__":
    main()
