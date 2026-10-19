# ─── Сборка ──────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Устанавливаем системные зависимости для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY pyproject.toml .

# Устанавливаем зависимости в отдельную директорию
RUN pip install --no-cache-dir --prefix=/install \
    fastapi "uvicorn[standard]" \
    sqlalchemy psycopg2-binary psycopg alembic \
    bcrypt python-dotenv \
    jinja2 python-multipart itsdangerous requests

# ─── Финальный образ ─────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Системные библиотеки для runtime (libpq для psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные зависимости из builder
COPY --from=builder /install /usr/local

# Копируем код приложения
COPY app.py .
COPY backend/ backend/
COPY frontend/ frontend/
COPY alembic.ini .

# Создаём директорию для аватарок (на случай отсутствия в репозитории)
RUN mkdir -p frontend/static/images/users_avatars

EXPOSE 8000

# Запускаем миграции, затем приложение
CMD ["sh", "-c", "alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port 8000"]
