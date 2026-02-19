# Enrichment Pipeline: Setup, Verification & Operations Guide

This guide walks through how to configure, run, and verify the enrichment pipeline end-to-end. It covers the LangGraph orchestrator, Perplexity research provider, confidence scoring, and the enrichment API.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Setup](#2-environment-setup)
3. [Start Infrastructure](#3-start-infrastructure)
4. [Verify Database Tables](#4-verify-database-tables)
5. [Running the Orchestrator Locally](#5-running-the-orchestrator-locally)
6. [Using the Enrichment API](#6-using-the-enrichment-api)
7. [Perplexity Research Gateway](#7-perplexity-research-gateway)
8. [Confidence Scoring & Promotion](#8-confidence-scoring--promotion)
9. [Monitoring Jobs & Cache](#9-monitoring-jobs--cache)
10. [Admin Operations](#10-admin-operations)
11. [Celery Workers & Scheduled Tasks](#11-celery-workers--scheduled-tasks)
12. [End-to-End Smoke Test](#12-end-to-end-smoke-test)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites

| Dependency      | Required | Purpose                                |
|-----------------|----------|----------------------------------------|
| Python 3.11+    | Yes      | Runtime                                |
| Docker          | Yes      | PostgreSQL, Redis, MinIO, Meilisearch  |
| langgraph       | Yes      | LangGraph orchestrator state machine   |
| Firecrawl key   | Yes      | Web scraping (page fetching)           |
| Perplexity key  | No       | URL discovery (falls back to stub)     |
| Groq/OpenAI key | Yes      | LLM-based data extraction              |

Install the Python dependency:

```bash
pip install langgraph
```

Verify it's importable:

```python
python -c "from langgraph.graph import StateGraph; print('LangGraph OK')"
```

---

## 2. Environment Setup

Add these variables to your `.env` file. The pipeline works in two modes:

### Stub mode (no Perplexity key)

URL discovery uses heuristic paths derived from the institution's website (e.g., `{website}/admissions`, `{website}/graduate/programs`). Good for testing.

### Full mode (with Perplexity key)

URL discovery calls the Perplexity Sonar API to find real, relevant URLs for each category. Produces much better results.

```bash
# --- Required for pipeline ---
FIRECRAWL_API_KEY=fc-your-key           # Web scraping
GROQ_API_KEY=gsk_your-key              # LLM extraction (or use OPENAI_API_KEY)

# --- Optional: enables real URL discovery ---
PERPLEXITY_API_KEY=pplx-your-key       # Perplexity Sonar API
RESEARCH_MAX_CONCURRENT=3              # Max parallel research requests

# --- Pipeline tuning ---
SCRAPE_RATE_LIMIT_PER_MINUTE=15        # Per-domain rate limit
SCRAPE_CONCURRENT_DOMAINS=5            # Domains scraped in parallel
USE_SCRAPING_ORCHESTRATOR=true         # Use LangGraph orchestrator
```

### Getting API Keys

- **Firecrawl**: Sign up at [firecrawl.dev](https://firecrawl.dev), copy API key from dashboard
- **Perplexity**: Sign up at [perplexity.ai](https://docs.perplexity.ai), create API key under Settings > API
- **Groq**: Sign up at [console.groq.com](https://console.groq.com), create API key

---

## 3. Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Verify everything is running
docker-compose ps
```

Expected services:
- `guidr-postgres` on port 5433
- `guidr-redis` on port 6379
- `guidr-meilisearch` on port 7700
- `guidr-minio` on ports 9000 (API) / 9001 (console)
- `guidr-celery-worker` consuming queues: default, scraping, processing, pipeline
- `guidr-celery-beat` for scheduled tasks

Run migrations:

```bash
alembic upgrade head
```

---

## 4. Verify Database Tables

The pipeline uses 8 tables created by migration 014. Verify they exist:

```bash
python -c "
from src.db import SessionLocal
from src.models import (
    PipelineJob, SourceDocument, RawArtifact,
    ExtractionRun, EntityPromotion, EnrichmentCache, DomainHealth
)
db = SessionLocal()
for model in [PipelineJob, SourceDocument, RawArtifact, ExtractionRun, EntityPromotion, EnrichmentCache, DomainHealth]:
    count = db.query(model).count()
    print(f'{model.__tablename__:25s}  rows: {count}')
db.close()
print('All pipeline tables OK')
"
```

Expected output: all tables exist with 0 rows (on first run).

---

## 5. Running the Orchestrator Locally

### 5a. Quick test: Run the graph directly (no Celery)

This is the fastest way to verify the LangGraph pipeline works. It runs synchronously in your terminal.

```python
from src.pipeline.orchestrator import create_orchestrator_graph

graph = create_orchestrator_graph()

# Run for a known institution (get an ID from your database)
result = graph.invoke({
    "job_id": "test-run-001",
    "entity_kind": "school",
    "entity_id": "<institution-uuid>",          # Replace with real UUID
    "category": "SCHOOL_OVERVIEW",
    "priority": "high",
    "schema_version": "v1",
    "retry_count": 0,
    "max_attempts": 3,
    "progress": [],
})

print("Status:", result.get("status"))
print("Confidence:", result.get("confidence"))
print("Progress steps:", result.get("progress"))
print("Extracted keys:", list((result.get("extracted") or {}).keys()))
```

What to expect:
- `progress` lists every node that ran: `['load_context', 'discover_urls', 'canonicalize_urls', 'fetch_page', 'store_raw', 'extract_structured', 'validate', 'score_confidence', 'stage_write', 'promote_write']`
- `confidence` is a float between 0.0 and 1.0
- `extracted` contains the structured data pulled from the scraped page
- `status` is `"success"` if the pipeline completed

### 5b. Run via Celery task

This is how the pipeline runs in production. The enrichment API dispatches jobs to this task.

```bash
# Terminal 1: Start the Celery worker
celery -A src.workers.celery_app worker -l info -Q default,scraping,processing,pipeline
```

```python
# Terminal 2: Dispatch a job
from src.db import SessionLocal
from src.pipeline.repositories.job_repository import JobRepository

db = SessionLocal()
repo = JobRepository(db)

# Create a pipeline job
job = repo.create_job(
    job_type="enrichment",
    entity_kind="school",
    entity_id="<institution-uuid>",
    priority="high",
    freshness_bucket="30d",
    input_json={"category": "SCHOOL_OVERVIEW"},
)
db.commit()
print(f"Created job: {job.id}")

# Dispatch to Celery
from src.pipeline.tasks.orchestrator_tasks import run_enrichment_pipeline
run_enrichment_pipeline.delay(str(job.id))
print("Job dispatched to Celery")
db.close()
```

Watch the Celery worker logs in Terminal 1 to see the pipeline execute node by node.

### 5c. Check job result after Celery runs

```python
from src.db import SessionLocal
from src.pipeline.repositories.job_repository import JobRepository

db = SessionLocal()
repo = JobRepository(db)
job = repo.get_job("<job-id>")

print(f"Status:  {job.status}")
print(f"Attempt: {job.attempt}")
print(f"Output:  {job.output_json}")
print(f"Error:   {job.error_message}")
db.close()
```

---

## 6. Using the Enrichment API

The API is the primary way users and the frontend trigger enrichment. Start the API server:

```bash
uvicorn src.main:app --reload --port 8000
```

### 6a. Trigger enrichment for a single entity

```bash
curl -X POST http://localhost:8000/pipeline/enrich \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_kind": "school",
    "entity_id": "<institution-uuid>",
    "priority": "high",
    "force_refresh": false
  }'
```

Possible responses:

| status              | Meaning                                   |
|---------------------|-------------------------------------------|
| `cache_hit`         | Fresh data exists in cache, returned it   |
| `enqueued`          | New job created and dispatched to Celery  |
| `dedup_in_progress` | A job for this entity is already running  |
| `quota_exceeded`    | User hit daily enrichment limit (50/day)  |

Example `enqueued` response:

```json
{
  "status": "enqueued",
  "message": null,
  "cache": null,
  "job": {
    "job_id": "a1b2c3d4-...",
    "status": "queued",
    "priority": "high"
  }
}
```

### 6b. Poll job status

```bash
curl http://localhost:8000/pipeline/jobs/<job-id> \
  -H "Authorization: Bearer <your-jwt-token>"
```

Response:

```json
{
  "job_id": "a1b2c3d4-...",
  "status": "succeeded",
  "progress": ["load_context", "discover_urls", "canonicalize_urls", "fetch_page", "store_raw", "extract_structured", "validate", "score_confidence", "stage_write", "promote_write"],
  "confidence": 0.892,
  "error": null,
  "queued_at": "2026-02-19T12:00:00",
  "started_at": "2026-02-19T12:00:01",
  "finished_at": "2026-02-19T12:00:15"
}
```

### 6c. Check cache status

```bash
curl "http://localhost:8000/pipeline/cache/status?entity_kind=school&entity_id=<uuid>" \
  -H "Authorization: Bearer <your-jwt-token>"
```

### 6d. Get cached value

```bash
curl "http://localhost:8000/pipeline/cache/value?entity_kind=school&entity_id=<uuid>" \
  -H "Authorization: Bearer <your-jwt-token>"
```

### 6e. Batch enrichment (shortlist)

Enrich up to 20 entities at once (e.g., a user's saved schools):

```bash
curl -X POST http://localhost:8000/pipeline/enrich/shortlist \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"entity_kind": "school", "entity_id": "<uuid-1>", "priority": "high"},
      {"entity_kind": "school", "entity_id": "<uuid-2>", "priority": "bulk"},
      {"entity_kind": "program", "entity_id": "<uuid-3>", "priority": "high"}
    ]
  }'
```

---

## 7. Perplexity Research Gateway

The Research Gateway is used by the orchestrator's `discover_urls` and `repair_extraction` nodes to find relevant URLs for an entity.

### 7a. Check which provider is active

```python
from src.pipeline.research_gateway.service import _select_provider

provider = _select_provider()
print(f"Active provider: {type(provider).__name__}")
# PerplexityProvider  -> real API (PERPLEXITY_API_KEY is set)
# PerplexityStubProvider -> heuristic fallback (no key)
```

### 7b. Test the Research Gateway directly

```python
from src.pipeline.research_gateway import ResearchGatewayService, ResearchRequest
from src.pipeline.research_gateway.schemas import EntityContext, Constraints

service = ResearchGatewayService()

req = ResearchRequest(
    job_type="URL_DISCOVERY",
    entity=EntityContext(
        entity_type="SCHOOL",
        name="Stanford University",
        website_hint="https://stanford.edu",
    ),
    category="SCHOOL_OVERVIEW",
    constraints=Constraints(max_results=5),
)

resp = service.run(req)
print(f"Status: {resp.status}")
print(f"Found {len(resp.results)} URLs:")
for r in resp.results:
    print(f"  {r.confidence:.2f}  {r.url}")
    print(f"         reason: {r.reason}")
```

With the **stub provider**, you'll get heuristic URLs like:
```
  0.90  https://stanford.edu/about
  0.80  https://stanford.edu/admissions
```

With the **real Perplexity provider**, you'll get actual discovered URLs:
```
  0.95  https://www.stanford.edu/about/
  0.90  https://admission.stanford.edu/
  0.85  https://facts.stanford.edu/
```

### 7c. Test repair flow

```python
req = ResearchRequest(
    job_type="REPAIR_EXTRACTION",
    entity=EntityContext(
        entity_type="SCHOOL",
        name="MIT",
        website_hint="https://mit.edu",
    ),
    category="PROGRAM_REQUIREMENTS",
    constraints=Constraints(max_results=5),
)

resp = service.run(req)
print(f"Repair found {len(resp.results)} alternative URLs")
```

### 7d. Verify Redis caching

The Research Gateway caches responses in Redis for 7 days. Run the same request twice:

```python
# First call: hits Perplexity API (or stub)
resp1 = service.run(req)
print(f"Cache hit: {resp1.metrics.cache_hit}")  # False

# Second call: returns cached result
resp2 = service.run(req)
print(f"Cache hit: {resp2.metrics.cache_hit}")  # True
```

### 7e. Verify source_documents persistence

After running URL discovery, check that discovered URLs were saved:

```python
from src.db import SessionLocal
from src.models.source_document import SourceDocument

db = SessionLocal()
docs = db.query(SourceDocument).order_by(SourceDocument.created_at.desc()).limit(10).all()
for d in docs:
    print(f"  {d.entity_kind}/{d.entity_id}  {d.canonical_url}  (by: {d.discovered_by})")
db.close()
```

---

## 8. Confidence Scoring & Promotion

The pipeline uses a weighted confidence score to decide what happens with extracted data.

### Formula

```
confidence = 0.35 * source_score + 0.35 * extraction_score + 0.25 * validation_score + 0.05 * staleness_score
```

| Component   | Weight | What it measures                                      |
|-------------|--------|-------------------------------------------------------|
| Source      | 0.35   | Is the URL from the entity's official domain?         |
| Extraction  | 0.35   | How many expected fields were populated?              |
| Validation  | 0.25   | Did the data pass business rule checks?               |
| Staleness   | 0.05   | How recently was the page fetched?                    |

### Thresholds

| Confidence   | Action                                             |
|--------------|-----------------------------------------------------|
| >= 0.85      | Auto-promote to production tables (institutions, programs, etc.) |
| 0.70 - 0.84  | Stage in `enrichment_cache`, skip promotion         |
| < 0.70       | Trigger repair flow (find alternative URLs)         |

### Test the scorer manually

```python
from src.pipeline.processors import ConfidenceScorer
from src.pipeline.processors.validator import ValidationResult
from datetime import datetime

scorer = ConfidenceScorer()

# Simulate a good extraction from an official .edu page
conf = scorer.compute(
    entity_kind="school",
    extracted={
        "description": "A leading research university...",
        "acceptance_rate": 4.3,
        "enrollment_total": 17534,
        "grad_enrollment": 9390,
        "campus_setting": "Suburban",
        "academic_calendar": "Quarter",
    },
    validation_result=ValidationResult(passed=True, status="passed", errors=[]),
    source_url="https://www.stanford.edu/about/",
    entity_website="https://stanford.edu",
    fetched_at=datetime.utcnow(),
)

print(f"Confidence: {conf}")                     # ~0.95
print(f"Should promote: {scorer.should_promote(conf)}")  # True
print(f"Should stage:   {scorer.should_stage(conf)}")    # False
print(f"Should repair:  {scorer.should_repair(conf)}")   # False
```

### Verify promotion happened

After a successful pipeline run with confidence >= 0.85:

```python
from src.db import SessionLocal
from src.models.entity_promotion import EntityPromotion

db = SessionLocal()
promos = db.query(EntityPromotion).order_by(EntityPromotion.promoted_at.desc()).limit(5).all()
for p in promos:
    print(f"  {p.entity_kind}/{p.entity_id}  promoted at {p.promoted_at}")
    print(f"  diff: {p.diff_json}")
db.close()
```

### Verify extraction runs

```python
from src.models.extraction_run import ExtractionRun

db = SessionLocal()
runs = db.query(ExtractionRun).order_by(ExtractionRun.created_at.desc()).limit(5).all()
for r in runs:
    print(f"  {r.entity_kind}  conf={r.confidence}  status={r.status}  extractor={r.extractor_name}")
db.close()
```

---

## 9. Monitoring Jobs & Cache

### List recent pipeline jobs

```python
from src.db import SessionLocal
from src.models.pipeline_job import PipelineJob

db = SessionLocal()
jobs = db.query(PipelineJob).order_by(PipelineJob.created_at.desc()).limit(10).all()
for j in jobs:
    print(f"  {j.id}  {j.status:10s}  {j.entity_kind}/{j.entity_id}  attempt={j.attempt}")
db.close()
```

### Check enrichment cache

```python
from src.models.enrichment_cache import EnrichmentCache

db = SessionLocal()
entries = db.query(EnrichmentCache).order_by(EnrichmentCache.computed_at.desc()).limit(10).all()
for e in entries:
    print(f"  {e.entity_kind}/{e.entity_id}  conf={e.confidence}  expires={e.expires_at}  hits={e.hit_count}")
db.close()
```

### Check raw artifacts stored in MinIO

```python
from src.models.raw_artifact import RawArtifact

db = SessionLocal()
artifacts = db.query(RawArtifact).order_by(RawArtifact.fetched_at.desc()).limit(10).all()
for a in artifacts:
    print(f"  {a.id}  {a.artifact_type}  {a.byte_size}B  {a.storage_uri}")
    print(f"    from: {a.fetched_from_url}")
db.close()
```

You can also browse raw files in the MinIO console at http://localhost:9001 (login: minioadmin / minioadmin).

---

## 10. Admin Operations

Admin endpoints require an admin JWT token.

### Force refresh an entity (bypasses quota and cache)

```bash
curl -X POST http://localhost:8000/pipeline/admin/refresh \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"entity_kind": "school", "entity_id": "<uuid>", "priority": "high"}'
```

### Rerun a failed job

```bash
curl -X POST http://localhost:8000/pipeline/admin/jobs/<job-id>/rerun \
  -H "Authorization: Bearer <admin-token>"
```

### Cancel a queued job

```bash
curl -X POST http://localhost:8000/pipeline/admin/jobs/<job-id>/cancel \
  -H "Authorization: Bearer <admin-token>"
```

### View domain health

```bash
curl http://localhost:8000/pipeline/admin/domains \
  -H "Authorization: Bearer <admin-token>"
```

Response shows per-domain scraping health:

```json
[
  {
    "host": "www.stanford.edu",
    "last_ok_at": "2026-02-19T12:00:15",
    "last_error_at": null,
    "error_streak": 0,
    "block_detected": false,
    "next_allowed_at": null
  }
]
```

### Purge expired cache

```bash
curl -X POST "http://localhost:8000/pipeline/admin/cache/purge?max_age_days=30" \
  -H "Authorization: Bearer <admin-token>"
```

---

## 11. Celery Workers & Scheduled Tasks

### Worker setup

**Development** (single worker, all queues):
```bash
celery -A src.workers.celery_app worker -l info -Q default,scraping,processing,pipeline
```

**Production** (specialized workers via docker-compose):
```bash
# Start with production profile for dedicated pipeline worker
docker-compose --profile production up -d
```

This starts two workers:
- `celery-worker`: handles default, scraping, processing queues
- `celery-worker-pipeline`: dedicated to the pipeline queue

### Celery Beat (scheduled tasks)

```bash
# Already runs via docker-compose, or manually:
celery -A src.workers.celery_app beat -l info
```

| Task                                     | Schedule              | What it does                          |
|------------------------------------------|-----------------------|---------------------------------------|
| `pipeline.refresh_stale`                 | Monday 3:00 UTC       | Re-scrape institutions >30 days old   |
| `ingestion.scorecard`                    | Wednesday 4:00 UTC    | Enrich from College Scorecard         |
| `search.reindex`                         | Sunday 5:00 UTC       | Reindex Meilisearch                   |
| `pipeline.maintenance.purge_expired_cache` | Daily 2:00 UTC       | Delete expired enrichment cache rows  |
| `pipeline.maintenance.reset_domain_health` | Saturday 3:00 UTC    | Reset stale domain blocks             |
| `pipeline.maintenance.cleanup_old_jobs`  | 1st of month 4:00 UTC | Archive pipeline jobs >90 days old    |

### Run maintenance tasks manually

```python
from src.pipeline.tasks.maintenance_tasks import (
    purge_expired_cache,
    reset_domain_health,
    cleanup_old_jobs,
)

# Run synchronously (for testing)
result = purge_expired_cache()
print(result)  # {"purged": 0}

result = reset_domain_health()
print(result)  # {"domains_reset": 0}

result = cleanup_old_jobs(days=90)
print(result)  # {"deleted": 0, "cutoff_days": 90}
```

---

## 12. End-to-End Smoke Test

This is a complete walkthrough to verify the entire pipeline from data load to enriched results.

### Step 1: Load foundation data

```bash
python scripts/load_scorecard_schools.py --limit 5
```

### Step 2: Get an institution ID

```python
from src.db import SessionLocal
from src.models.institution import Institution

db = SessionLocal()
school = db.query(Institution).first()
print(f"ID:      {school.id}")
print(f"Name:    {school.name}")
print(f"Website: {school.website_url}")
print(f"Scraped: {school.last_scraped_at}")
db.close()
```

### Step 3: Start the API server and Celery worker

```bash
# Terminal 1
uvicorn src.main:app --reload --port 8000

# Terminal 2
celery -A src.workers.celery_app worker -l info -Q default,scraping,processing,pipeline
```

### Step 4: Trigger enrichment via API

```bash
curl -X POST http://localhost:8000/pipeline/enrich \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"entity_kind": "school", "entity_id": "<uuid-from-step-2>", "priority": "high"}'
```

Save the `job.job_id` from the response.

### Step 5: Watch the Celery worker logs

In Terminal 2, you should see the orchestrator execute each node:
```
INFO: Dispatched orchestrator pipeline for job <id>
INFO: Perplexity discovered 5 URLs for <school>/SCHOOL_OVERVIEW in 1200ms
INFO: Confidence for school: source=1.00 ext=0.83 val=1.00 stale=1.00 -> 0.891
```

### Step 6: Poll job status until complete

```bash
curl http://localhost:8000/pipeline/jobs/<job-id> \
  -H "Authorization: Bearer <token>"
```

Wait for `"status": "succeeded"`.

### Step 7: Verify the data

```python
from src.db import SessionLocal
from src.models.institution import Institution

db = SessionLocal()
school = db.query(Institution).filter(Institution.id == "<uuid>").first()
print(f"Name:            {school.name}")
print(f"Description:     {school.description[:100] if school.description else 'None'}...")
print(f"Acceptance rate: {school.acceptance_rate}")
print(f"Enrollment:      {school.enrollment_total}")
print(f"Last scraped:    {school.last_scraped_at}")
print(f"Scrape status:   {school.scrape_status}")
db.close()
```

### Step 8: Check all pipeline artifacts

```python
from src.db import SessionLocal
from src.models.enrichment_cache import EnrichmentCache
from src.models.extraction_run import ExtractionRun
from src.models.entity_promotion import EntityPromotion
from src.models.raw_artifact import RawArtifact
from src.models.source_document import SourceDocument

db = SessionLocal()
entity_id = "<uuid>"

# Source documents (discovered URLs)
docs = db.query(SourceDocument).filter(SourceDocument.entity_id == entity_id).all()
print(f"\nSource documents: {len(docs)}")
for d in docs:
    print(f"  {d.canonical_url}  (by {d.discovered_by})")

# Raw artifacts (fetched content)
artifacts = db.query(RawArtifact).order_by(RawArtifact.fetched_at.desc()).limit(5).all()
print(f"\nRaw artifacts: {len(artifacts)}")
for a in artifacts:
    print(f"  {a.storage_uri}  ({a.byte_size} bytes)")

# Extraction runs
runs = db.query(ExtractionRun).filter(ExtractionRun.entity_id == entity_id).all()
print(f"\nExtraction runs: {len(runs)}")
for r in runs:
    print(f"  conf={r.confidence}  status={r.status}  extractor={r.extractor_name}")

# Enrichment cache
cache = db.query(EnrichmentCache).filter(EnrichmentCache.entity_id == entity_id).all()
print(f"\nCache entries: {len(cache)}")
for c in cache:
    print(f"  conf={c.confidence}  expires={c.expires_at}  hits={c.hit_count}")

# Promotions (audit trail)
promos = db.query(EntityPromotion).filter(EntityPromotion.entity_id == entity_id).all()
print(f"\nPromotions: {len(promos)}")
for p in promos:
    print(f"  promoted at {p.promoted_at}  diff: {list(p.diff_json.keys())}")

db.close()
```

### Step 9: Verify cache hit on second request

```bash
# Request enrichment again - should return cache_hit
curl -X POST http://localhost:8000/pipeline/enrich \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"entity_kind": "school", "entity_id": "<uuid>", "priority": "high"}'
```

Expected response: `"status": "cache_hit"` with the cached data in the `cache` field.

### Step 10: Check the frontend

Visit the school or program detail page in the frontend. You should see:
- An **EnrichmentBadge** showing "Updated X ago" (green) for fresh data
- If data is stale, it shows "Data may be outdated" with a Refresh button

---

## 13. Troubleshooting

### Pipeline job stuck in "queued"

The Celery worker isn't consuming the `pipeline` queue.

```bash
# Check worker is running and listening to the pipeline queue
celery -A src.workers.celery_app inspect active_queues

# If missing, restart with pipeline queue
celery -A src.workers.celery_app worker -l info -Q default,scraping,processing,pipeline
```

### Pipeline job fails with "Circuit breaker open"

A domain has too many consecutive errors and is temporarily blocked.

```python
# Check which domains are blocked
from src.pipeline.services.domain_health_service import DomainHealthService
service = DomainHealthService()
health = service.get_all_health()
blocked = [d for d in health if d["block_detected"]]
print(f"Blocked domains: {blocked}")
```

To manually unblock:
```python
from src.db import SessionLocal
from src.models.domain_health import DomainHealth

db = SessionLocal()
db.query(DomainHealth).filter(DomainHealth.host == "blocked-host.edu").update({
    DomainHealth.block_detected: False,
    DomainHealth.error_streak: 0,
    DomainHealth.next_allowed_at: None,
})
db.commit()
db.close()
```

### Pipeline job fails with "Failed to fetch URL"

- Check if the Firecrawl API key is set and valid
- Check if the URL is reachable (some universities block bots)
- Check robots.txt compliance: `curl https://university.edu/robots.txt`

### "No target URL" error

The orchestrator couldn't find any URL to scrape. This happens when:
- The institution has no `website_url` in the database
- URL discovery returned no results (stub provider needs a `website_hint`)
- Fix: ensure institutions have `website_url` set (College Scorecard data includes this)

### Perplexity API returns empty results

- Verify your API key: `echo $PERPLEXITY_API_KEY`
- Check API quota at [perplexity.ai/settings](https://www.perplexity.ai/settings/api)
- The stub provider will be used as fallback if the key is invalid

### Confidence too low (data not promoted)

If confidence is consistently below 0.85:
- Check source score: is the URL from the institution's own domain?
- Check extraction score: are enough fields being extracted? (run extractor directly to debug)
- Check validation: are business rule checks failing?

```python
from src.pipeline.processors import ConfidenceScorer
scorer = ConfidenceScorer()

# Check individual components
print("Source:", scorer.score_source("https://other-site.com/stanford", "https://stanford.edu"))  # 0.4
print("Source:", scorer.score_source("https://stanford.edu/about", "https://stanford.edu"))       # 1.0
```

### Quota exceeded

Users are limited to 50 enrichment requests per day. Admins bypass this via `/pipeline/admin/refresh`.

```python
# Check current quota usage
from src.pipeline.redis_keyspace.quota import get_quota_usage
usage = get_quota_usage("user-uuid", resource="enrich", period="day")
print(f"Used: {usage}")
```

### Redis connection errors

```bash
# Verify Redis is running
docker-compose ps redis
redis-cli ping  # Should return PONG
```

The pipeline is designed to fail open: if Redis is unavailable, quota checks and circuit breakers are skipped (pipeline still works, just without those safety nets).

---

## Related Documentation

- [Pipeline Guide](PIPELINE_GUIDE.md) - Architecture overview, scraping workflow, storage layout
- [Quick Start](QUICK_START.md) - Getting started with data loading and basic pipeline
- [Comprehensive Data Collection Guide](COMPREHENSIVE_DATA_COLLECTION_GUIDE.md) - Agent-based collection
