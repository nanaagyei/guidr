# Deploying the Guidr backend to Railway

This deploys the FastAPI API, a Celery worker, and Celery beat — all from this
repo/Dockerfile — plus managed Postgres and Redis. Frontend deploys separately
to Vercel and points at the API URL.

> Prereqs: a Railway account, the Railway CLI (`npm i -g @railway/cli`) optional,
> and your API keys ready (College Scorecard, OpenAlex, Perplexity, Groq/OpenAI).
> Do **not** commit real secrets — set them in Railway's Variables tab.

---

## 1. Create the project + data plugins

1. Create a new Railway project → **Deploy from GitHub repo** → pick this repo,
   root directory `guidr-backend`.
2. In the project, **+ New → Database → Add PostgreSQL**.
3. **+ New → Database → Add Redis**.

Railway exposes these as reference variables:
`${{Postgres.DATABASE_URL}}` and `${{Redis.REDIS_URL}}`.

> **pgvector:** migration `010` runs `CREATE EXTENSION IF NOT EXISTS vector`
> (also `pgcrypto`, `citext`). Railway's Postgres image includes pgvector, so
> this succeeds automatically. If it ever errors, add the `pgvector` extension
> to the Postgres service and re-deploy.

---

## 2. Configure the API service

The GitHub deploy created one service — this is the **API**. It picks up
`railway.toml` (Dockerfile build, start `python run.py`, healthcheck `/health`).

Set its **Variables** (from `.env.production.example`):

| Variable | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `ENV` | `production` |
| `ALLOWED_ORIGINS` | `https://<your-vercel-domain>,http://localhost:3000` |
| `COLLEGE_SCORECARD_API_KEY` | your key |
| `OPENALEX_API_KEY` | your key |
| `PERPLEXITY_API_KEY` | your key (real recommendations) |
| `GROQ_API_KEY` **or** `OPENAI_API_KEY` | your key (LLM extraction) |
| `SMTP_*`, `R2_*` | optional (see env template) |

`run.py` runs `alembic upgrade head` on boot, so **the schema is created on the
first successful deploy**. Watch the deploy logs for "Database migrations applied
successfully" and a healthy `/health`.

---

## 3. Add the Celery worker service

**+ New → GitHub Repo → same repo**, root `guidr-backend`. Then:

- **Settings → Deploy → Custom Start Command:**
  ```
  celery -A src.workers.celery_app worker -l info -Q default,scraping,processing,pipeline --pool=prefork -c 2
  ```
- **Variables:** same as the API service. Fastest: use Railway's **"Shared
  Variables"** at the project level for the common keys, and reference them, or
  copy the API service's variables.
- It needs `DATABASE_URL` and `REDIS_URL` (the pipeline/dossier jobs run here).

## 4. Add the Celery beat service (scheduler)

Same as the worker, but start command:
```
celery -A src.workers.celery_app beat -l info
```
Run **exactly one** beat instance (`numReplicas = 1`).

> Tip: put all shared keys in **Project → Shared Variables** so the three
> services stay in sync; only `DATABASE_URL`/`REDIS_URL` come from the plugins.

---

## 5. Seed real data (run once, after the API is healthy)

Open the **API service → ⋮ → Shell** (or `railway run` locally against the prod
env). Start small to keep the catalog complete-looking and fast:

```bash
# 1) Schools (College Scorecard). Start with a test batch, then scale up.
python scripts/load_scorecard_schools.py --limit 50
# later, full/by-state:
# python scripts/load_scorecard_schools.py --state CA

# 2) Schools + programs together (IPEDS + Scorecard + program scrape)
python scripts/batch_seed.py --ipeds --limit 200
python scripts/batch_seed.py --programs --max-per-school 10

# (optional) verify pipeline wiring
python scripts/verify_pipeline_setup.py
```

**Professors** are not bulk-seeded — they populate **on demand** via the
dossier/professor-match pipeline (OpenAlex + Perplexity) when a user runs
Recommendations and saves a result. This requires the **worker** running and
`OPENALEX_API_KEY` + `PERPLEXITY_API_KEY` set. To pre-warm, create a test user,
complete the profile to level 2, and run Recommendations once.

> Meilisearch is optional for v1 — the `/schools` and `/programs` routes fall
> back to DB filtering when search is unconfigured. Add a Meilisearch service
> later and run `python scripts/reindex_search.py` if you want fast search.

---

## 6. Connect the frontend (Vercel)

1. Copy the API service's public URL (Railway → API service → Settings →
   Networking → Generate Domain), e.g. `https://guidr-api.up.railway.app`.
2. In Vercel, set `NEXT_PUBLIC_API_URL` to that URL for the frontend project.
3. Add the Vercel domain to the API's `ALLOWED_ORIGINS` and redeploy the API
   (cookies are httpOnly + cross-site, so CORS `allow_credentials` must match the
   exact origin — no trailing slash).

---

## 7. Smoke test

- `GET https://<api>/health` → `{"status":"ok"}`
- Register a user on the Vercel frontend → check the DB has the row.
- Browse `/schools` and `/institutions` → results appear (after seeding).
- Complete profile to level 2 → run Recommendations → confirm real (non-synthetic)
  results and that a professor match job runs on the worker (check worker logs).

## Rollback / ops notes

- Migrations are forward-only via `run.py`; a bad deploy won't roll back schema.
  Test migrations on a staging DB if you change models.
- Scale: bump worker `-c` concurrency or `numReplicas` as load grows; keep beat at 1.
- Logs: API, worker, and beat each have their own logs in Railway.
