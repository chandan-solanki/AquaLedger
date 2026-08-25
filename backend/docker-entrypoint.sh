#!/bin/sh
# Sprint 18 Session 3 - single-instance deploy entrypoint. Running
# migrations here (rather than as a separate compose step or a manual
# "remember to run this first") is safe specifically because the process
# model decision for this VPS is one backend container / one Uvicorn
# worker - there is no second instance that could race this same
# `alembic upgrade head` concurrently on container start.
set -eu

echo "[entrypoint] Applying database migrations..."
alembic upgrade head

echo "[entrypoint] Starting Uvicorn (single worker - see DEPLOYMENT.md for why)..."
# No --proxy-headers/--forwarded-allow-ips here: this backend is never
# directly reachable from the browser or from the nginx reverse proxy in
# this architecture (the Next.js BFF is the only caller, over the internal
# Docker network) - there is no untrusted intermediary sending
# X-Forwarded-* headers to this process for uvicorn to need to trust or
# distrust. See DEPLOYMENT.md's "Reverse proxy" section for where that
# trust boundary actually lives.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
