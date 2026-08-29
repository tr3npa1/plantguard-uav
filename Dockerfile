FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip wheel --wheel-dir /wheelhouse .

FROM python:3.12-slim AS runtime

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLANTGUARD_ENVIRONMENT=production \
    PLANTGUARD_LOG_FORMAT=json \
    PLANTGUARD_API__HOST=0.0.0.0

RUN groupadd --system plantguard \
    && useradd --system --gid plantguard --create-home --home-dir /home/plantguard plantguard

WORKDIR /app

COPY --from=builder /wheelhouse /wheelhouse
RUN python -m pip install --no-index --find-links=/wheelhouse plantguard-uav \
    && rm -rf /wheelhouse \
    && mkdir -p /app/artifacts /app/data \
    && chown plantguard:plantguard /app/artifacts /app/data

COPY configs ./configs
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

EXPOSE 8000

VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2).close()"]

USER plantguard

ENTRYPOINT ["plantguard-uav"]
