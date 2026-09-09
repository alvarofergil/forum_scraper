FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system forum && adduser --system --ingroup forum forum

COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN python -m pip install --upgrade pip && python -m pip install -e .

RUN mkdir -p /app/config /app/data /app/backups \
    && chown -R forum:forum /app/config /app/data /app/backups

USER forum

ENTRYPOINT ["python", "-m", "app"]
CMD ["status"]
