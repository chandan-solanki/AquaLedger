# syntax=docker/dockerfile:1

# Sprint 18 Session 3 - production image for the FastAPI backend.
#
# Two-stage build: `builder` resolves the locked, production-only
# dependency set with uv (fast, reproducible via uv.lock); `runtime` is a
# slim image carrying only the resulting virtualenv, the application
# source, and the native libraries WeasyPrint needs at *runtime* (not
# just at build time - PDF/statement export, app.core.report_export,
# calls into libpango/libcairo/libgdk-pixbuf on every request that hits
# it, not only during image build).
#
# NOT build-verified in this session - no Docker daemon was available in
# this development environment. Package names below follow WeasyPrint's
# own documented Debian/Ubuntu dependency list; confirm the exact names
# against whichever Debian release the `python:3.13-slim` tag resolves to
# at actual build time (they have shifted between Debian releases before,
# e.g. `libgdk-pixbuf2.0-0` vs `libgdk-pixbuf-2.0-0`), and treat the first
# real `docker build` on the deployment host as the verification step
# this session could not perform.

FROM python:3.13-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder

RUN pip install --no-cache-dir uv
WORKDIR /app

# Dependency layer cached separately from application code so an app-only
# change doesn't force a full dependency re-resolve/reinstall.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

FROM base AS runtime

RUN useradd --create-home --uid 1000 --user-group appuser
WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app /app
COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh \
    # document_storage_root (app.core.document_engine.storage) and the
    # structlog file handlers (app.core.logging, logs/app.log +
    # logs/error.log) both write relative to the app's own working
    # directory - both need to exist and be writable by the non-root user
    # before the volumes declared in docker-compose.prod.yml are mounted
    # over them.
    && mkdir -p /app/storage/documents /app/logs \
    && chown -R appuser:appuser /app/storage /app/logs

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
