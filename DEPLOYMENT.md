# AquaLedger — Production Deployment Guide

Prepared in Sprint 18 Session 3. Target machine: **Oracle Cloud "Always
Free" Ubuntu VPS, 1 vCPU, 6 GB RAM**, with PostgreSQL, the FastAPI
backend, and the Next.js frontend all co-located on that one box.

**Scope note:** this document prepares the repository and explains the
deployment. It deliberately stops short of the actual VPS provisioning,
domain, and HTTPS steps — those are Session 4. Nothing in this guide has
been run against a real Docker daemon (none was available in the
environment this was written in); the first real `docker build`/`docker
compose up` on the VPS is the verification step this session could not
perform itself. Where something *could* be verified without Docker (the
Next.js standalone build, the health/readiness endpoints, the database
pool reasoning), it was — see the Session 3 report for what was actually
run and observed.

---

## 1. Architecture recap

```
Browser
   │  HTTPS (Session 4: nginx + certbot, not yet configured)
   ▼
frontend container (Next.js, standalone output)  ── the ONLY container
   │  plain HTTP, over the Docker-internal network    with a published port
   ▼
backend container (FastAPI / Uvicorn, 1 worker)   ── never publicly reachable
   │  asyncpg
   ▼
postgres container (PostgreSQL 16)                ── never publicly reachable
```

This shape is not assumed — it's what the actual code does. Every
backend call happens from Next.js Route Handlers / Server Components
(`frontend/src/lib/auth/authenticated-backend-request.ts` and the
sibling BFF helpers), never from the browser directly; the one
client-side HTTP client that *could* talk to the backend directly
(`frontend/src/lib/api-client.ts`) has zero importers anywhere in the
codebase. So only the frontend needs a public port; the backend and
database stay off the public internet entirely.

## 2. Required packages on the VPS

- Docker Engine + the Docker Compose plugin (`docker compose`, not the
  standalone `docker-compose` v1 binary — this guide's commands assume
  the plugin form). Follow Docker's official Ubuntu install
  instructions for the current Ubuntu LTS.
- Nothing else needs to be installed on the host itself — PostgreSQL,
  the backend, and the frontend all run inside containers built from
  this repo. A reverse proxy (nginx) and TLS (certbot) are **not**
  installed by this session's scope; that's Session 4.

## 3. Getting the code onto the VPS

Clone the repository (or pull a release) to a working directory, e.g.
`/opt/aqualedger`. Everything below assumes commands run from the repo
root.

## 4. Environment configuration

Three separate `.env` files are needed — this is not duplicated
configuration, it reflects three genuinely different consumers:

| File | Consumed by | Purpose |
|---|---|---|
| `.env` (repo root, from `.env.production.example`) | `docker compose` itself | Postgres credentials + frontend build args (`${VAR}` substitution in `docker-compose.prod.yml`) |
| `backend/.env` (from `backend/.env.production.example`) | The FastAPI process (`pydantic-settings`) | Everything the app reads via `Settings` |
| `frontend/.env.production.example` | Documentation only — its values are the same `NEXT_PUBLIC_*` build args already listed in the root `.env` | Explains why those values must be *build* args, not runtime env |

**Copy and fill in:**

```bash
cp .env.production.example .env
cp backend/.env.production.example backend/.env
```

**The Postgres credentials in both files must match** — nothing keeps
`POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` in the root `.env` in
sync with the same values embedded in `backend/.env`'s `DATABASE_URL`
automatically. Set them once, then copy the same values into both.

### Production secrets

Generate a real JWT secret on the VPS itself, never reuse the example:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Paste the result into `backend/.env`'s `JWT_SECRET_KEY`. Choose a strong,
unique `POSTGRES_PASSWORD` the same way. **Never commit `.env`,
`backend/.env`, or any file with real secrets** — the repo's `.gitignore`
already blocks this for every filename pattern except the checked-in
`*.example` templates.

## 5. Backend process model: why one Uvicorn worker

**Decision: exactly one Uvicorn worker process**, set explicitly in
`backend/docker-entrypoint.sh` (`--workers 1`), not left to a default.

This was not assumed — three independent, evidence-backed reasons all
point the same way on this specific box:

1. **FastAPI is async, not sync-WSGI.** The common "`2 × cores + 1`"
   worker-count formula is a *sync worker* heuristic (each sync worker
   can serve exactly one request at a time, so you need enough of them
   to cover concurrency). An async ASGI worker already multiplexes many
   concurrent I/O-bound requests on one event loop without blocking. On
   1 physical vCPU, a second worker process would only time-slice the
   same core — no real parallelism gained for I/O-bound work, and CPU-
   bound work (PDF rendering) was moved off the event loop via
   `asyncio.to_thread` in Sessions 1–2, not by adding processes.
2. **The in-process login rate limiter would silently break.**
   `InMemoryLoginRateLimiter` (`backend/app/modules/auth/security.py`)
   keeps its hit-counting state in a plain Python `dict`, scoped to one
   process. A second worker means a second, independent copy of that
   dict — an attacker could halve (or worse) the effective rate limit
   just by landing requests on different worker processes. This is a
   correctness/security defect, not merely a resource concern, and it
   is the strongest reason to stay at one worker even if the VPS later
   gets more CPU.
3. **Each worker owns its own DB connection pool.** N workers × the
   pool settings below would multiply toward PostgreSQL's
   `max_connections` faster than intended (see §6).

No Gunicorn supervisor was added in front of Uvicorn either: Gunicorn's
job (supervising and restarting multiple worker processes) has nothing
to supervise here — Docker's own `restart: unless-stopped` already
supervises the single container/process. Adding Gunicorn would be
supervising a supervisor for no benefit at this scale.

**If the VPS is ever upgraded to more vCPUs**, revisit this — but first
replace `InMemoryLoginRateLimiter` with a shared store (this session
deliberately did not do that; it's out of scope, since nothing here
demonstrated a need for more than one worker yet).

## 6. Database connection pool

`backend/app/db/session.py`'s `create_async_engine(...)` already sets
`pool_pre_ping=True` (transparently detects and replaces a dead
connection before use) — kept as-is; no `pool_recycle` was added, since
Postgres runs on the same host with no intermediate load balancer or
firewall known to silently drop idle connections, and `pool_pre_ping`
already covers the realistic failure mode here.

**Pool size changed via `backend/.env.production.example`, not code**:
`DATABASE_POOL_SIZE=5`, `DATABASE_MAX_OVERFLOW=5` (was 10/20 by default
— fine for local dev, oversized for one production worker):

- **Maximum connections from this backend process: 10** (`5 + 5`).
- PostgreSQL's own default `max_connections` is 100 — 10 leaves ample
  headroom for `psql`/monitoring access and a future second service,
  while comfortably covering this app's actual concurrency pattern
  (short-lived queries, no long-held transactions, one worker process).
- This is not so small that it would serialize ordinary traffic: 10
  concurrent in-flight queries is well above what one Uvicorn worker
  handling typical ERP request rates needs at once.
- The code default in `backend/app/core/config.py` (10/20) was
  deliberately **not** changed — that default is fine for local
  development (a single developer, no memory pressure) and changing it
  would be an unrelated, unjustified edit; the production template is
  where the production-specific value belongs.

## 7. Next.js: standalone output

`next.config.ts` now sets `output: "standalone"`. Verified directly
(without Docker) this session:

```bash
cd frontend
npm run build
# .next/standalone/server.js exists
# .next/standalone/node_modules/ contains only the traced subset next
#   determined this app actually needs (16 top-level entries, not the
#   full node_modules tree)
cp -r .next/static .next/standalone/.next/static
cp -r public .next/standalone/public
cd .next/standalone && PORT=3099 HOSTNAME=127.0.0.1 node server.js
```

Confirmed working: `/login` renders (200), a static asset under
`public/` loads (200), and — most importantly — the BFF layer works
identically to `next start`: `/api/auth/login`, `/api/auth/session`, an
authenticated `/api/boats` call, and an invoice PDF download via
`/api/invoices/{id}/document` all succeeded against the real dev
database and a real backend instance. Nothing about authentication
cookies, BFF proxying, or PDF generation is standalone-mode-specific —
the standalone server is the same Next.js server, just packaged
differently for deployment.

**`frontend/Dockerfile`** builds on this: a `deps` stage installs
`node_modules` from the lockfile, a `builder` stage runs `next build`
with the `NEXT_PUBLIC_*` build args baked in, and a `runner` stage
copies only `public/`, `.next/standalone`, and `.next/static` into a
slim `node:22-slim` image, running as a non-root user.

**Known constraint, not a bug**: because `NEXT_PUBLIC_API_URL` (and the
other `NEXT_PUBLIC_*` values) are inlined into the client bundle at
`next build` time, **the frontend image must be rebuilt — not just
restarted with new env vars — if the backend URL ever changes.**

## 8. Docker images

- **`backend/Dockerfile`**: two-stage, `python:3.13-slim` base. The
  `builder` stage uses `uv sync --frozen --no-dev` for a reproducible,
  production-only dependency install; the `runtime` stage adds the
  native libraries WeasyPrint needs *at request time*
  (`libcairo2`, `libpango-1.0-0`, `libpangocairo-1.0-0`,
  `libgdk-pixbuf-2.0-0`, `libffi8`, `shared-mime-info`,
  `fonts-liberation`), creates a non-root `appuser`, and runs
  `docker-entrypoint.sh` (`alembic upgrade head` then `exec uvicorn
  ... --workers 1`).
- **`frontend/Dockerfile`**: three-stage (`deps`/`builder`/`runner`) as
  described above, non-root `nextjs` user.
- **Neither image's exact `apt`/system-package names have been
  build-verified** (no Docker available here) — WeasyPrint's own
  documented Debian/Ubuntu package list was used, but package names have
  shifted between Debian releases before (e.g.
  `libgdk-pixbuf2.0-0` vs `libgdk-pixbuf-2.0-0`). **The first real
  `docker build` on the VPS is required to confirm these resolve
  correctly** against whatever Debian release the `python:3.13-slim` tag
  currently points to.

## 9. `docker-compose.prod.yml`

Three services — `postgres`, `backend`, `frontend` — a named volume each
for Postgres data, backend document storage, and backend logs, and
health-checked startup ordering:

- `backend` `depends_on: postgres: condition: service_healthy` (via
  Postgres's own `pg_isready`) — not a bare `depends_on:`, so the
  backend's `alembic upgrade head` startup step never races an
  still-initializing database.
- `frontend` `depends_on: backend: condition: service_healthy` (via the
  new `/health/ready` endpoint) — the frontend doesn't need the backend
  to serve its own static assets, but there's no reason to accept
  traffic before the one thing it actually depends on can serve
  requests.
- Only `frontend` publishes a port (`3000:3000`) to the host, per the
  network-topology reasoning in §1.
- **No `deploy.resources.limits`** — that's a Swarm-mode construct that
  plain `docker compose up` does not enforce outside Swarm; assuming
  otherwise was explicitly the mistake this session was told to avoid.
  **No `mem_limit`/`cpus` either** (the classic-Compose alternative that
  *is* respected outside Swarm) — a hard memory cap risks the OOM killer
  taking down a container during a legitimate burst (e.g. concurrent PDF
  exports) instead of gracefully leaning on the swap file recommended in
  §10. Revisit only if real production memory pressure is observed.

**Not build/run-verified** — validated only as syntactically well-formed
YAML (parsed successfully with PyYAML) in this environment. Run `docker
compose -f docker-compose.prod.yml config` on the VPS as a first sanity
check before `up`.

## 10. Swap

**Recommendation: add a 4 GB swap file** on the VPS before first deploy.

- **What it protects against**: an OOM safety net, not additional
  working memory. Estimated combined idle footprint of Postgres +
  Uvicorn (WeasyPrint's Cairo/Pango bindings loaded in-process) +
  Next.js is roughly 500 MB–1 GB; a real burst (several concurrent
  Next.js SSR requests plus one PDF export in flight) could reasonably
  spike toward 1.5–2.5 GB. Without swap, hitting the 6 GB ceiling means
  the Linux OOM killer picks a process to kill — quite possibly
  Postgres, mid-write, which is a far worse outcome than temporarily
  degraded latency.
- **Why not more**: swap is disk-speed-slow. A box that's *steadily*
  relying on several GB of swap is a box that needs more RAM, not more
  swap — 4 GB is sized as a burst absorber, not a substitute for
  physical memory.
- Set `vm.swappiness=10` alongside it, so the kernel only reaches for
  swap under real pressure rather than proactively swapping out warm
  Postgres shared buffers or the Uvicorn process during normal
  operation.

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

**Not run on the development machine** — this is deployment
documentation for the VPS, per this session's explicit scope.

## 11. Reverse proxy (prerequisite only — Session 4 configures this)

Only the frontend container needs to sit behind nginx; the backend never
does (§1). When Session 4 sets this up, nginx will terminate TLS
(certbot) and proxy to `frontend:3000`. Nothing in the current codebase
depends on `X-Forwarded-*` headers being set (no code reads
`request.client.host` on the frontend side, and the backend's own
`request.client.host` usage — see §12 — is a separate, already-existing
limitation unrelated to nginx), but setting the conventional
`X-Forwarded-For`/`X-Forwarded-Proto`/`X-Forwarded-Host` headers when
proxying is still the correct default for any future need.

Until this is live, do not browser-test login against the VPS's bare IP
over `http://` — session cookies are set `Secure` in production, and
unlike `localhost` (exempted by browsers as a secure context), a plain
IP address won't get the cookie sent back on the next request. See §15
for how Session 4 confirmed this and the workaround (SSH tunnel) for
smoke-testing before TLS is configured.

## 12. Known limitation, documented not fixed this session

`backend/app/common/request_context.py` builds each request's audit-log
`ip_address` from `request.client.host` directly, with no
`X-Forwarded-For` parsing anywhere in the backend. In this architecture,
the backend's only caller is the frontend container itself (§1) — so
`request.client.host` at the backend will always be the frontend
container's internal Docker-network IP, **never the real end user's
IP**, regardless of any reverse proxy configuration in front of the
frontend. Fixing this would require the Next.js BFF layer to forward the
real client IP in a header and the backend to explicitly trust and parse
it from that one internal caller — a real (if narrow) behavior change to
what audit logs record, deliberately left out of this scaffolding
session rather than folded in unannounced. Flagged here for a future,
explicitly-scoped session.

## 13. Operational commands

```bash
# Bring everything up (build images if needed), detached:
docker compose -f docker-compose.prod.yml up -d --build

# Check status:
docker compose -f docker-compose.prod.yml ps

# Tail logs (all services, or one):
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml logs -f backend

# Restart one service after a config change:
docker compose -f docker-compose.prod.yml restart backend

# Stop everything (containers removed, named volumes kept):
docker compose -f docker-compose.prod.yml down

# Apply a new backend release (rebuild + recreate only what changed):
docker compose -f docker-compose.prod.yml up -d --build backend
```

Database migrations run automatically on backend container start
(`docker-entrypoint.sh` → `alembic upgrade head`) — safe specifically
because there is exactly one backend instance (§5), so this can never
race a second instance's own migration attempt.

## 14. Explicitly deferred to later sessions

- Real VPS provisioning, domain, nginx, and TLS/certbot (Session 4).
- Log rotation for `backend/logs/app.log`/`error.log` (flagged in
  Session 1's audit, not addressed here — file-based logs are still
  useful inside the `backend_logs` volume for now, but will grow
  unbounded).
- The audit-log real-client-IP limitation (§12).
- Any per-container CPU/memory limits, should real production pressure
  ever justify them (§9).
- Redis/Celery/any job queue, database query rewrites, cursor
  pagination, SQL timing instrumentation — all explicitly out of scope
  per this session's own instructions.
- Report/statement export's redundant aggregate re-computation across
  pages (§15) — real, but a lower-frequency path than list/dashboard
  endpoints, and the correct fix reshapes pagination across ~9 report
  types; deferred rather than risking a financial-reporting regression
  in a deployment-scaffolding session.
- Gating `/docs`/`/redoc`/`/openapi.json` behind `is_production` (§15)
  — currently always enabled, mitigated today only by the backend never
  publishing a host port; revisit if that topology assumption ever
  changes.

## 15. Sprint 18 Session 4 — Production Verification & Caching Audit

This session ran the stack natively (no Docker daemon available in this
environment either — same constraint as Session 3) in a
production-shaped configuration (`APP_ENV=production`, `DEBUG=false`,
`DATABASE_POOL_SIZE=5`/`DATABASE_MAX_OVERFLOW=5`, standalone Next.js
build) and did a full route-by-route Next.js caching audit, a backend
repeated-query audit, and a live concurrency/resource check. Full detail
is in the Session 4 chat report; the operationally relevant deltas from
§§1-14 above:

- **DB pool confirmed applied at runtime, not just documented**: built
  the SQLAlchemy engine directly with the production env values and
  read back `engine.pool.size()` / `engine.pool._max_overflow` — both
  matched (5/5). A 20-concurrent-request burst against an endpoint that
  each need a connection completed with zero errors (11-21ms each),
  confirming SQLAlchemy queues excess acquisitions rather than erroring
  once the pool is exhausted.
- **Caching audit finding, fixed this session**: 8 of the BFF's binary
  document/export proxy routes (`/api/documents/[id]/download`,
  `/api/reports/export`, and the `*/document` routes for invoices,
  payments, purchase bills, supplier payments, delivery challans,
  purchase orders) were missing the `Cache-Control: private, no-store`
  header that `/api/company-profile/logo` and `/api/profile/avatar`
  already carried from Session 1's audit. Added the same header to all
  8 for consistency — verified live: a real invoice PDF download now
  returns `cache-control: private, no-store`.
- **Caching audit finding, no code change needed**: every authenticated
  page is forced dynamic by `AppLayout`'s one `cookies()` call; every
  BFF route forwards the caller's own access-token cookie to the
  backend and fetches with `cache: "no-store"`; there is no
  `revalidate`/`unstable_cache`/ISR anywhere in the app. Confirmed
  against a real `next build`'s own route table (every `(authenticated)`
  route marked `ƒ`, `/login` and `/_not-found` marked `○`). No
  authenticated/tenant-specific JSON or document response can be served
  from a shared cache to a different user at the Next.js layer.
- **Backend N+1 finding, fixed this session**: `InvoiceService.get_document_context`
  (the invoice-PDF path) looked up each line item's fish one at a time
  via `FishService.get()` in a loop — N queries for N distinct fish per
  invoice — instead of the batched `FishService.get_many_by_ids()` the
  same file already uses elsewhere for the identical purpose. Fixed to
  batch; added unit tests proving the lookup is now a single call and
  that a genuinely-missing fish still raises the expected error.
- **Backend finding, documented not fixed**: report/statement export
  (`_fetch_all_pages` in `reports/export_dispatch.py`) re-runs each
  report's *entire* service method per page purely to walk pagination,
  which re-computes page-independent aggregates (opening balance,
  summary totals) once per page instead of once total. Real but
  lower-frequency (export/statement generation, not list/dashboard
  traffic) and the correct fix reshapes pagination for ~9 report types
  — deferred (see §14) rather than risking a reporting-correctness bug
  in this session.
- **Security finding, documented, not a blocker**: `FastAPI()` never
  sets `docs_url`/`redoc_url`/`openapi_url`, so Swagger/ReDoc/the raw
  OpenAPI schema stay reachable regardless of `APP_ENV`/`DEBUG`. Not
  exploitable today because the backend container publishes no host
  port (§1, §9) — nothing outside the Docker network can reach `/docs`
  at all — but worth gating explicitly if that topology assumption
  changes.
- **Operational note for Session 5's first smoke test**: production
  session cookies are set with `Secure` (correct hygiene). Browsers
  (and `curl`) special-case `localhost` as a secure context, so testing
  against `http://localhost:3000` works even without TLS — confirmed
  live in this session. The literal VPS IP address does **not** get
  that exemption: a browser hitting `http://<vps-ip>:3000` before nginx
  + certbot (§11) is live will receive the login cookies but never send
  them back, so login will appear broken. Session 5 should either wait
  until HTTPS is live to browser-test, or use an SSH tunnel
  (`ssh -L 3000:localhost:3000 ...`) so the browser sees `localhost`.
- **Live verification performed**: login, session check, dashboard,
  fish list, a create-then-list-then-delete-then-list round trip
  (proving no server-side staleness — the deleted record disappeared
  on the very next fetch), an invoice PDF download (full
  browser→Next.js standalone→BFF→FastAPI→PostgreSQL→WeasyPrint chain),
  and platform-admin-vs-regular-tenant-user access control (`200` vs
  `403` on `/api/platform/tenants`) — all against real dev data via two
  throwaway verification accounts, soft-deleted (`status='inactive'`,
  `deleted_at` set — not hard-deleted, to preserve the append-only
  `audit_logs` rows their logins generated) after use.
- **Resource baseline caveat unchanged from Session 3**: measured on
  this Windows dev machine (6 cores/12 threads, 16 GB RAM), not the
  target 1 vCPU/6 GB Linux VPS, and Docker itself remains unavailable in
  this environment — so container-level `docker stats` numbers still
  cannot be produced here. Native process RSS only: uvicorn worker
  ~168-175 MB, Next.js standalone `node server.js` ~124-136 MB, all 8
  Postgres backend/postmaster processes combined ~46 MB — negligible
  growth (a few MB) observed across a login+dashboard+20-concurrent-request
  burst, i.e. no leak signal, but these are not Linux-container numbers
  and must not be read as a VPS prediction.
