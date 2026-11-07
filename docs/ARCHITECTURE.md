# Guidr architecture

> Updated 2026-11-07. Describes the code as it is. For product scope see
> [`POSITIONING.md`](POSITIONING.md).

The repository is a monorepo with two packages:

```
guidr/
├── guidr-backend/     FastAPI API, research pipeline, Celery workers, Alembic migrations
├── guidr-frontend/    Next.js 15 App Router app (React 19, TypeScript, Tailwind)
├── docs/              Cross-package documents (this file, POSITIONING.md, validation/)
├── .github/           CI workflows, Dependabot, PR template (the only workflows that run)
├── .pre-commit-config.yaml
└── release-please-config.json, .release-please-manifest.json
```

## Backend (`guidr-backend/`)

FastAPI with **synchronous** SQLAlchemy sessions, PostgreSQL 15 (with the `vector`, `pgcrypto` and
`citext` extensions), Redis 7, Celery and Alembic.

| Path | What lives there |
|---|---|
| `src/main.py` | The `FastAPI` app: middleware, CORS, startup checks, and `app.include_router(...)` for every router |
| `src/config.py` | `Settings` (pydantic-settings, read from the environment at import). `settings.is_production` is `env == "production"`. Feature flags are the `enable_*` fields |
| `src/db.py` | Engine, `SessionLocal`, and the `get_db` dependency |
| `src/routes/*.py` | One `APIRouter` per area (auth, profile, academic_records, schools, programs, essays, recommendations, professors, dossiers, pipeline, research, …), each registered in `src/main.py` |
| `src/models/*.py` | SQLAlchemy models, all inheriting `Base` from `src/models/base.py`, with UUID primary keys; most are re-exported in `src/models/__init__.py` |
| `src/schemas/` | Pydantic request/response schemas |
| `src/dependencies/` | FastAPI dependencies: `auth.py` (`get_current_user`, `require_admin_user`), `feature_gate.py` (`require_level`), `rate_limit.py` |
| `src/services/` | Business logic used by routes (dossier, enrichment, search, storage, email, …) |
| `src/middleware/` | Global rate limiter |
| `src/utils/` | Password hashing and strength, JWT, two-factor codes, profile completion |
| `src/workers/celery_app.py` | Celery app, task routing (queues `default`, `scraping`, `processing`, `pipeline`), task annotations, beat schedule |
| `src/pipeline/research_gateway/` | Provider abstraction for research calls (Perplexity → OpenAI-compatible deep research → stub in development only), with Redis + Postgres caching |
| `src/pipeline/orchestrator/` | LangGraph graphs: dossier, professor match, standard enrichment |
| `src/pipeline/tasks/` | Celery tasks that run the graphs and maintenance jobs |
| `src/pipeline/{clients,extractors,processors,repositories,prompts,redis_keyspace,scraping,services,schemas}/` | Pipeline building blocks; the scraping path is off by default (`enable_bulk_scrape`, `enable_scrape_fallback`) |
| `src/scrapers/` | Legacy scrapers (not the primary path) |
| `alembic/versions/NNN_snake_case_name.py` | Migrations, numbered sequentially. Run `alembic heads`, use the next free number, set `down_revision` to the current head, and write a working `downgrade()` |
| `scripts/` | Seeding and maintenance scripts (`load_scorecard_schools.py`, `batch_seed.py`, `reindex_search.py`, …) |
| `tests/` | Pytest suite: `tests/routes/` (API tests), `tests/pipeline/`, and top-level tests |
| `run.py` | Production entry point: `alembic upgrade head`, then uvicorn on `$PORT` |
| `Dockerfile`, `railway.toml`, `DEPLOY_RAILWAY.md` | Deployment (Railway: api, worker, beat services) |

**Auth.** A JWT in an httpOnly `session` cookie; protect routes with `Depends(get_current_user)`.

**Route tests** follow `tests/routes/test_dossier_routes.py`: `TestClient(app)` with
`app.dependency_overrides` for `get_current_user` and `get_db` (a `MagicMock` session) and
`src.dependencies.rate_limit._get_redis` patched. Note that `tests/pipeline/conftest.py` replaces
`src.db` with a mock for the whole run.

## Frontend (`guidr-frontend/`)

| Path | What lives there |
|---|---|
| `src/app/**/page.tsx` | App Router pages (all client-rendered; there is no `middleware.ts`, so pages redirect unauthenticated users client-side) |
| `src/components/` | Components; `src/components/ui/` holds shared primitives, `src/components/landing/` and `src/components/marketing/` the public pages |
| `src/utils/api.ts` | Every backend call goes through a helper here (`fetchWithCredentials`, cookies included) |
| `src/contexts/` | `AuthContext`, `ProfileCompletionContext`, `ToastContext` (`useToast`) |
| `src/hooks/`, `src/lib/`, `src/styles/` | Hooks, utilities (`cn`), global styles |
| `src/components/Sidebar.tsx` | App navigation; `comingSoon` marks gated features |
| `DEPLOY_VERCEL.md` | Deployment (Vercel); `NEXT_PUBLIC_API_URL` points at the API |

Scripts: `npm run dev`, `npm run lint` (zero warnings), `npm run typecheck`, and `npm run check`
(lint + typecheck + production build). There is no frontend test suite.

## CI (`.github/workflows/`)

| Workflow | Runs | Steps |
|---|---|---|
| `ci.yml` | PRs and pushes to `main`, `release/**` | **Pre-commit** (`pre-commit run --all-files`: merge-conflict, YAML, end-of-file, whitespace, large files, ruff, frontend lint, frontend typecheck); **Backend** (`ruff check src tests`, `pytest` with Postgres 15 and Redis 7 services); **Frontend** (`npm ci`, `npm run check`) |
| `security.yml` | PRs, pushes, weekly | gitleaks (full history; historic findings allowlisted by fingerprint in `.gitleaksignore`), Trivy (fails on fixable CRITICAL), `pip-audit` and `npm audit` (reported, not failing) |
| `codeql.yml` | PRs, pushes to `main` and `release/**`, and a schedule | CodeQL analysis |
| `release-please.yml` | Pushes to `main` | Opens the release PR from Conventional Commits |

Backend CI environment: `DATABASE_URL`, `JWT_SECRET` (32+ characters), `REDIS_URL` and `ENV=test`
must be exported, because settings are read at import.

## Branches, pull requests and commits

- Branch from `release/dev`; open the PR against `main`.
- Conventional Commit titles (`type(scope): summary`); release-please computes versions from them.
- Use the PR template (`.github/pull_request_template.md`): what and why, type of change,
  checklist (Conventional title, changelog, `pre-commit run --all-files`, no secrets).
- Run `pre-commit run --all-files` before pushing. Never commit secrets or `.env` files.

## Changelogs

Practice today: **two hand-written, per-package changelogs**, `guidr-backend/CHANGELOG.md` and
`guidr-frontend/CHANGELOG.md`. Each change adds an entry under `## [Unreleased]`, in the matching
`### Added / Changed / Fixed / Removed / Security` section:

```
- [YYYY-MM-DD UTC] type(scope): Summary (#issue)
  - Detail bullets
  - Files: `path/one.py`, `path/two.tsx`
```

Release-please is configured to write a root `CHANGELOG.md` as well. How the three relate is
being decided in #71; record the decision here when it lands.
