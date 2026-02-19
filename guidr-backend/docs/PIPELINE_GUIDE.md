# Guidr Data Pipeline Guide

This guide explains how the Guidr data pipeline works, how to set it up, and how to pull and work with data.

## Architecture Overview

The pipeline follows a three-zone architecture:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   RAW ZONE      │     │  STAGING ZONE    │     │  PRODUCTION ZONE    │
│   (MinIO/S3)    │────▶│  (PostgreSQL     │────▶│  (PostgreSQL        │
│                 │     │   staging schema)│     │   public schema)    │
│ • Scraped HTML  │     │                  │     │                     │
│ • Raw JSON      │     │ • Validated data │     │ • institutions      │
│ • Audit trail   │     │ • Pending review │     │ • programs          │
└─────────────────┘     └──────────────────┘     │ • professors        │
                                                  │ • funding_opps     │
                                                  └─────────────────────┘
```

### Data Flow

1. **Ingestion**: College Scorecard API and Firecrawl web scraping fetch data.
2. **Raw Storage**: All scraped content is stored in MinIO (`guidr-data-lake` bucket).
3. **Processing**: Extractors parse content; Validator, Transformer, and Enricher process it.
4. **Staging** (optional): Data can be held in `staging.staging_records` for review.
5. **Production**: Approved data is written to `institutions`, `programs`, `professors`, `funding_opportunities`.

---

## Prerequisites

- **Python 3.11+**
- **Docker** (for PostgreSQL, Redis, MinIO, Meilisearch)
- **API Keys**:
  - College Scorecard: [api.data.gov/signup](https://api.data.gov/signup/)
  - Firecrawl: [firecrawl.dev](https://firecrawl.dev)

---

## Quick Setup

### 1. Start Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5433)
- Redis (6379)
- Meilisearch (7700)
- MinIO (9000 API, 9001 console)
- Celery worker
- Celery Beat

### 2. Configure Environment

Copy `.env.example` to `.env` and set:

```bash
# Required
DATABASE_URL=postgresql://guidr_user:guidr_password@localhost:5433/guidr_db
JWT_SECRET=your-secret-here

# Pipeline (required for scraping)
COLLEGE_SCORECARD_API_KEY=your-scorecard-key
FIRECRAWL_API_KEY=your-firecrawl-key

# MinIO (defaults work with docker-compose)
MINIO_ENDPOINT=localhost
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=guidr-data-lake
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 3b. Verify Setup

```bash
python scripts/verify_pipeline_setup.py
```

This creates:
- Production tables (`institutions`, `programs`, `professors`, etc.)
- `staging` schema with `staging_records`
- `scrape_jobs`, `funding_opportunities`
- `professor_programs` association table

### 4. Reset Pipeline Data (Optional)

To wipe previously scraped data and start fresh:

```bash
python scripts/reset_pipeline_data.py --dry-run   # Preview
python scripts/reset_pipeline_data.py --yes       # Execute (requires confirmation without --yes)
```

### 5. Load Foundation Data

```bash
# CLI (no auth): Load graduate schools from College Scorecard
python scripts/load_scorecard_schools.py --limit 100
python scripts/load_scorecard_schools.py --state CA

# Or via API (requires admin token)
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"limit": 100}'

# Or run synchronously (small batch)
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"state": "CA", "limit": 50, "async_run": false}'
```

### 6. Run the Scraping Pipeline

```bash
# Trigger full pipeline for one institution
curl -X POST http://localhost:8000/ingestion/pipeline/run \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"institution_id": "<uuid>"}'

# Batch pipeline for multiple institutions
curl -X POST http://localhost:8000/ingestion/pipeline/batch \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"institution_ids": ["<uuid1>", "<uuid2>"]}'
```

---

## Pipeline Components

### 1. Scraping Orchestrator

Centralizes URL discovery and robots.txt checks:

```python
from src.pipeline.scraping import ScrapingOrchestrator

orchestrator = ScrapingOrchestrator()
result = orchestrator.discover_graduate_pages("https://stanford.edu")
# result.discovered.overview, .programs, .faculty, .funding
```

### 2. Extractors

Parse scraped markdown into structured data:

- `FundingExtractor` – scholarships, fellowships, assistantships
- `FacultyExtractor` – professors, research interests
- `OverviewExtractor` – acceptance rate, enrollment, campus setting
- `ProgramExtractor` – graduate programs, requirements, deadlines

### 3. Processors

- **Validator**: Schema validation, business rules (e.g., funding amount 0–100k)
- **Transformer**: Date parsing, text cleanup, normalization
- **Enricher**: Metadata (source_url, data_source)

### 4. Storage

- **Raw (MinIO)**: `raw/YYYY/MM/DD/{institution_id}/{job_type}/`
- **Staging (PostgreSQL)**: `staging.staging_records` for review before promotion
- **Production**: `institutions`, `programs`, `professors`, `funding_opportunities`

### 5. Research Gateway (New)

URL discovery and deep research for scraping:

- `POST /internal/research/run` – Run URL_DISCOVERY or REPAIR_EXTRACTION
- Categories: SCHOOL_OVERVIEW, PROGRAM_REQUIREMENTS, FACULTY_DIRECTORY, PROGRAM_FUNDING, etc.
- Stub provider uses heuristic paths; configure Perplexity API for real discovery

### 6. LangGraph Orchestrator (New)

State machine workflow: discovery → fetch → extract → validate → promote.

- Celery task: `pipeline.run_orchestrator` with `institution_id`, `category`
- Requires `pip install langgraph`
- Repair loop for low-confidence extractions

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/internal/research/run` | POST | Research Gateway: URL discovery, repair extraction |
| `/ingestion/schools/scorecard/load` | POST | Load graduate schools from College Scorecard |
| `/ingestion/schools/scorecard` | POST | Enrich existing institutions with Scorecard financials |
| `/ingestion/schools/ipeds` | POST | Load from IPEDS data |
| `/ingestion/pipeline/run` | POST | Run full scrape pipeline for one institution |
| `/ingestion/pipeline/batch` | POST | Run pipeline for multiple institutions |
| `/ingestion/pipeline/jobs` | GET | List scrape jobs (filter by institution_id, status) |
| `/ingestion/pipeline/jobs/{id}` | GET | Get scrape job details |

---

## Celery Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `pipeline.run_orchestrator` | On-demand | LangGraph orchestrator for institution + category |
| `pipeline.refresh_stale` | Monday 3:00 UTC | Queue scrape for institutions not scraped in 30+ days |
| `ingestion.scorecard` | Wednesday 4:00 UTC | Enrich institutions with College Scorecard |
| `search.reindex` | Sunday 5:00 UTC | Reindex Meilisearch |

---

## Database Schemas

### Production (public)

- `institutions` – Schools (from Scorecard, enriched by scraping)
- `programs` – Graduate programs
- `professors` – Faculty
- `funding_opportunities` – Scholarships, fellowships, assistantships
- `professor_programs` – Professor–program associations
- `scrape_jobs` – Pipeline job audit

### Staging (staging schema)

- `staging_records` – Records pending promotion (entity_type, payload, validation_status, approved_at)

### Pipeline infra (migration 014)

- `source_documents` – Canonical URLs per entity + category
- `pipeline_jobs` – Unified job table (research, scrape, extract, validate, promote)
- `raw_artifacts` – Metadata for downloaded content (storage pointer)
- `extraction_runs` – LLM extraction results and confidence
- `enrichment_cache` – Cached enriched data per entity

---

## Raw Data Lake (MinIO)

Structure:

```
guidr-data-lake/
├── raw/
│   └── 2026/
│       └── 02/
│           └── 02/
│               └── {institution_id}/
│                   ├── overview/
│                   │   └── overview.md
│                   ├── funding/
│                   │   └── raw_pages.json
│                   ├── faculty/
│                   │   └── raw_pages.json
│                   └── programs/
│                       └── raw_pages.json
└── audit/
    └── scorecard_load/
        └── load_summary.json
```

Access MinIO console: http://localhost:9001

---

## Troubleshooting

**Pipeline not running**
- Ensure Celery worker is up: `docker-compose logs celery-worker`
- Check Redis: `docker-compose ps redis`

**MinIO connection refused**
- Start MinIO: `docker-compose up -d minio`
- Verify at http://localhost:9001

**Firecrawl 429**
- Reduce `SCRAPER_DELAY_SECONDS` or wait for rate limit reset

**No institutions to scrape**
- Load Scorecard data first: POST `/ingestion/schools/scorecard/load`
