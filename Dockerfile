FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/media /app/staticfiles /app/logs \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Runs migrations and collectstatic against whatever DJANGO_SETTINGS_MODULE/.env
# the container is started with, then hands off to gunicorn — kept out of the
# image build itself since collectstatic/config/settings/prod.py need real
# secrets that only exist at runtime, not at build time.
ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
