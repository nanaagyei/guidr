# Enrichment Pipeline: Setup & Verification

End-to-end verification guide for the LangGraph orchestrator, agentic dossier system, and all enrichment APIs.

---

## 1. Prerequisites

| Dependency | Required | Purpose |
|------------|----------|---------|
| Python 3.11+ | Yes | Runtime |
| Docker | Yes | PostgreSQL, Redis, MinIO, Meilisearch |
| langgraph | Yes | Orchestrator state machine |
| Perplexity key | **Recommended** | Primary research provider (DossierGraph, ProfessorMatchGraph, RecommendationGraph). Falls back to stub provider in dev. |
| College Scorecard key | Yes | Foundation school metadata load |
| Semantic Scholar key | Optional | Professor enrichment (h-index, papers, citations) |
| Firecrawl key | Legacy/Optional | Web scraping fallback — **disabled by default** (`ENABLE_SCRAPE_FALLBACK=false`) |

### Install LangGraph

```bash
pip install langgraph
python -c "from langgraph.graph import StateGraph; print('OK')"
```

---

## 2. Environment

```bash
# Required
DATABASE_URL=postgresql://guidr_user:guidr_password@localhost:5433/guidr_db
JWT_SECRET=your-secret
INTERNAL_API_KEY=your-internal-key      # python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Agentic research (primary — recommended)
PERPLEXITY_API_KEY=pplx-your-key

# Foundation data
COLLEGE_SCORECARD_API_KEY=your-key

# Professor matching (optional but recommended)
SEMANTIC_SCHOLAR_API_KEY=your-key      # OpenAlex is free, no key needed

# Scraping fallback (disabled by default — only enable if needed)
# ENABLE_SCRAPE_FALLBACK=false
# FIRECRAWL_API_KEY=fc-your-key
```

---

## 3. Start Infrastructure

```bash
docker-compose up -d
python run.py    # Auto-runs migrations, starts server on :8000
```

Verify services: `docker-compose ps` — expect postgres, redis, meilisearch, minio, celery-worker, celery-beat all running.

---

## 4. Verify Database Tables

```python
from src.db import SessionLocal
from src.models import (
    PipelineJob, SourceDocument, RawArtifact,
    ExtractionRun, EntityPromotion, EnrichmentCache, DomainHealth
)

db = SessionLocal()
for model in [PipelineJob, SourceDocument, RawArtifact, ExtractionRun, EntityPromotion, EnrichmentCache, DomainHealth]:
    count = db.query(model).count()
    print(f"{model.__tablename__:25s}  rows: {count}")
db.close()
print("All pipeline tables OK")
```

---

## 5. Load Foundation Data

```bash
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state": "CA", "limit": 10}'
```

Get an institution ID from the response or query the database.

---

## 6. Test DossierGraph (Direct)

Run the agentic dossier graph synchronously without Celery:

```python
import asyncio
from src.pipeline.orchestrator.dossier_graph import create_dossier_graph
from src.pipeline.orchestrator.dossier_state import DossierState

graph = create_dossier_graph()

# Minimal state for a school dossier
initial_state = DossierState(
    job_id="test-001",
    entity_kind="school_dossier",
    entity_id="<institution-uuid>",
    user_id="<user-uuid>",
    user_context={
        "primary_field_of_study": "Computer Science",
        "research_areas": ["Machine Learning", "NLP"],
        "country_of_citizenship": "US",
    },
    schema_version="v1",
    retry_count=0,
    max_attempts=3,
    progress=[],
)

result = asyncio.run(graph.ainvoke(initial_state))

print("Status:", result.get("status"))
print("Confidence:", result.get("confidence"))
print("Progress:", result.get("progress"))
print("Value keys:", list((result.get("value_json") or {}).keys()))
print("Citation count:", len(result.get("citations_json") or []))
```

Expected: `status` is `promoted` (confidence ≥ 0.78) or `staged` (0.55–0.77) or `staged_with_warning` (<0.55). Progress list shows all nodes that ran (load_context → research_extract → validate_citations → score_confidence → stage → promote).

---

## 7. Test via Celery

```bash
# Terminal 1: Start worker (research_fast + research_heavy + scholarly_api queues)
celery -A src.workers.celery_app worker -l info -Q default,research_fast,research_heavy,scholarly_api,pipeline
```

```python
# Terminal 2: Dispatch a dossier job
from src.pipeline.tasks.dossier_tasks import run_dossier_research

# School dossier
result = run_dossier_research.delay(
    entity_kind="school_dossier",
    entity_id="<institution-uuid>",
    user_id="<user-uuid>",
)
print(f"Task ID: {result.id}")
```

Watch the Celery worker logs to see the dossier graph execute node by node.

To poll job status via the API:

```bash
curl http://localhost:8000/pipeline/jobs/<task-id> \
  -H "Cookie: session=<user-jwt>"
```

---

## 8. Test Enrichment API

### Trigger enrichment

```bash
curl -X POST http://localhost:8000/pipeline/enrich \
  -H "Cookie: session=<user-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"entity_kind": "school", "entity_id": "<uuid>", "priority": "high"}'
```

Possible responses: `cache_hit`, `enqueued`, `dedup_in_progress`, `quota_exceeded`.

### Poll job status

```bash
curl http://localhost:8000/pipeline/jobs/<job-id> \
  -H "Cookie: session=<user-jwt>"
```

### Check cache

```bash
curl "http://localhost:8000/pipeline/cache/status?entity_kind=school&entity_id=<uuid>" \
  -H "Cookie: session=<user-jwt>"
```

### Batch enrichment

```bash
curl -X POST http://localhost:8000/pipeline/enrich/shortlist \
  -H "Cookie: session=<user-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"entity_kind": "school", "entity_id": "<uuid-1>", "priority": "high"},
      {"entity_kind": "school", "entity_id": "<uuid-2>", "priority": "bulk"}
    ]
  }'
```

---

## 9. Test Admin Endpoints

Admin endpoints accept either an admin session cookie or the `X-Internal-Key` header:

```bash
# Force refresh a stale entity
curl -X POST http://localhost:8000/pipeline/admin/refresh \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entity_kind": "school", "entity_id": "<uuid>"}'

# Rerun a failed job
curl -X POST http://localhost:8000/pipeline/admin/jobs/<job-id>/rerun \
  -H "X-Internal-Key: $INTERNAL_API_KEY"

# Cancel a queued job
curl -X POST http://localhost:8000/pipeline/admin/jobs/<job-id>/cancel \
  -H "X-Internal-Key: $INTERNAL_API_KEY"

# Domain health overview
curl http://localhost:8000/pipeline/admin/domains \
  -H "X-Internal-Key: $INTERNAL_API_KEY"

# Purge expired cache entries
curl -X POST http://localhost:8000/pipeline/admin/cache/purge \
  -H "X-Internal-Key: $INTERNAL_API_KEY"
```

---

## 10. Test Agentic Dossier System

### School dossier

```bash
curl -X POST http://localhost:8000/dossiers/schools/<school_id>/research \
  -H "Cookie: session=<user-jwt>"
```

### Professor matching

```bash
# research_areas are read automatically from the user's profile — no body needed
curl -X POST http://localhost:8000/dossiers/schools/<school_id>/professors/match \
  -H "Cookie: session=<user-jwt>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

The graph runs: OpenAlex author search (using profile `research_areas`) → Semantic Scholar enrichment → Perplexity synthesis + ranking.

Get all matched professors across your saved schools:

```bash
curl http://localhost:8000/dossiers/professors/recommended \
  -H "Cookie: session=<user-jwt>"
```

### Funding dossier

```bash
curl -X POST http://localhost:8000/dossiers/schools/<school_id>/funding/research \
  -H "Cookie: session=<user-jwt>"
```

Response includes two sections:
- `funding_opportunities` — institutional funding (TA/RA, fellowships, merit awards)
- `external_opportunities` — national fellowships filtered by `country_of_citizenship` and `primary_field_of_study` (NSF GRFP, NIH F31, NDSEG, Hertz, Ford Foundation, Fulbright, etc.)

### AI recommendations

```bash
curl -X POST http://localhost:8000/recommendations/request \
  -H "Cookie: session=<user-jwt>"
```

Returns `{"job_id": "...", "status": "queued"}`. Poll via `GET /pipeline/jobs/<job_id>`, then fetch results from `GET /recommendations/latest`.

### View application deadlines

```bash
curl http://localhost:8000/dossiers/deadlines \
  -H "Cookie: session=<user-jwt>"
```

All dossier endpoints return `{"status": "enqueued", "job_id": "..."}` or `{"status": "cache_hit", "cache": {...}}`.

### Verify citations in cache

```python
from src.db import SessionLocal
from src.models.enrichment_cache import EnrichmentCache

db = SessionLocal()
entry = db.query(EnrichmentCache).filter(
    EnrichmentCache.freshness_bucket.like("school_dossier%")
).order_by(EnrichmentCache.computed_at.desc()).first()

if entry:
    print(f"Confidence: {entry.confidence}")
    print(f"Citations: {len(entry.citations_json)} sources")
    print(f"Evidence map: {list(entry.evidence_map_json.keys())}")
db.close()
```

---

## 11. End-to-End Smoke Test

Run this sequence to verify the full agentic pipeline from foundation data through dossier + professors + funding:

```bash
# Step 1 — Load foundation data
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state": "MA", "limit": 3}'

# Step 2 — Note a school UUID from the response (or query for one)
curl "http://localhost:8000/schools?name=MIT" -H "X-Internal-Key: $INTERNAL_API_KEY"
# Copy the `id` field as SCHOOL_ID

# Step 3 — Register + log in a test user (skip if you have a session cookie)
curl -X POST http://localhost:8000/auth/2fa/send \
  -H "Content-Type: application/json" \
  -d '{"email": "smoke@example.com", "purpose": "register"}'

curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "smoke@example.com", "password": "Smoke123!", "full_name": "Smoke Test", "verification_code": "123456"}'

curl -c cookies.txt -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "smoke@example.com", "password": "Smoke123!"}'

# Step 4 — Set up user profile (drives all agentic research)
curl -X PUT http://localhost:8000/profile \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{
    "intended_degree": "phd",
    "primary_field_of_study": "Computer Science",
    "research_areas": ["Machine Learning", "NLP"],
    "career_goals": "Research scientist focused on language model safety",
    "country_of_citizenship": "US",
    "funding_priority": "must_have"
  }'

# Step 5 — Request AI recommendations
curl -X POST http://localhost:8000/recommendations/request -b cookies.txt
# Note the job_id

# Step 6 — Poll recommendations job, then fetch results
curl http://localhost:8000/pipeline/jobs/<job_id> -b cookies.txt
curl http://localhost:8000/recommendations/latest -b cookies.txt

# Step 7 — Request school dossier (async)
SCHOOL_ID=<uuid-from-step-2>
curl -X POST "http://localhost:8000/dossiers/schools/$SCHOOL_ID/research" -b cookies.txt

# Step 8 — Poll dossier job, then read from cache
curl http://localhost:8000/pipeline/jobs/<dossier_job_id> -b cookies.txt
curl "http://localhost:8000/pipeline/cache/value?entity_kind=school_dossier&entity_id=$SCHOOL_ID" \
  -b cookies.txt

# Step 9 — Match professors
curl -X POST "http://localhost:8000/dossiers/schools/$SCHOOL_ID/professors/match" \
  -b cookies.txt -H "Content-Type: application/json" -d '{}'

# Step 10 — Funding dossier
curl -X POST "http://localhost:8000/dossiers/schools/$SCHOOL_ID/funding/research" -b cookies.txt

# Step 11 — Verify cache entries in Python
python -c "
from src.db import SessionLocal
from src.models.enrichment_cache import EnrichmentCache
db = SessionLocal()
entries = db.query(EnrichmentCache).order_by(EnrichmentCache.computed_at.desc()).limit(5).all()
for e in entries:
    print(f'{e.entity_kind}  id={e.entity_id}  user={e.user_id}  conf={e.confidence:.2f}  status={e.status}')
db.close()
"

# Step 12 — Verify cache hit on repeat dossier request
curl -X POST "http://localhost:8000/dossiers/schools/$SCHOOL_ID/research" -b cookies.txt
# Expected: {"status": "cache_hit", ...}
```

---

## 12. Troubleshooting

**Jobs stuck in "queued"**: Celery worker not listening on the correct queue. Restart with `-Q default,research_fast,research_heavy,scholarly_api,pipeline`.

**Perplexity returns empty**: Verify key with `echo $PERPLEXITY_API_KEY`. Check quota at perplexity.ai/settings. Stub provider auto-activates as fallback for development.

**Confidence too low (staged or warned)**:
- `0.55–0.77` (staged): check citation quality and extraction completeness. No automatic repair — trigger manual repair from the dossier UI when the feature is available, or re-request with a more specific profile.
- `< 0.55` (staged-with-warning): citation quality is poor; data shown with "unverified" badge. Encourage user to verify with the school directly.

**Profile fields missing**: Professor matching and funding dossier quality degrades without `research_areas`, `primary_field_of_study`, and `country_of_citizenship`. Verify profile fields via `GET /profile`.

**No external funding results**: Check `country_of_citizenship` on the user profile. External fellowships are filtered by citizenship eligibility.

**Quota exceeded**: Users limited to 50 enrichment requests/day. Admins bypass via `POST /pipeline/admin/refresh` with `X-Internal-Key`.

**Redis connection errors**: `docker-compose ps redis`, `redis-cli ping`. Pipeline fails open if Redis is unavailable (quota/inflight-cap checks skipped).

**Circuit breaker open**: Only relevant if `ENABLE_SCRAPE_FALLBACK=true`. Check `GET /pipeline/admin/domains`. Reset stale blocks via the Saturday maintenance task or `POST /pipeline/admin/domains/<domain>/reset`.

---

## Related Docs

- [Quick Start](QUICK_START.md) — Get running in 10 minutes
- [Pipeline Guide](PIPELINE_GUIDE.md) — Architecture and components
- [R2 Setup](R2_SETUP.md) — Cloudflare R2 for document storage
- [Comprehensive Collection](COMPREHENSIVE_DATA_COLLECTION_GUIDE.md) — Agent-based collection
