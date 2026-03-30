# Guidr Data Pipeline Guide

Architecture, components, API reference, and agentic research workflows.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENTIC RESEARCH CORE                      │
│                                                                 │
│  User Profile (research_areas, career_goals, citizenship)       │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐   ┌──────────────────┐   ┌─────────────────┐  │
│  │Recomm-      │   │ School / Funding  │   │ Professor Match │  │
│  │endations    │   │ DossierGraph      │   │ Graph           │  │
│  │(Perplexity) │   │ (Perplexity +     │   │ (OpenAlex +     │  │
│  │             │   │  citation check)  │   │  S2 + synthesis)│  │
│  └──────┬──────┘   └────────┬─────────┘   └───────┬─────────┘  │
│         │                  │                      │            │
│         ▼                  ▼                      ▼            │
│    enrichment_cache (per-user, TTL-keyed, citations_json)       │
│         │                                                       │
│         ▼  confidence >= 0.78                                   │
│    production tables: institutions / programs / professors      │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │ foundation data only
┌────────┴────────┐
│ College         │
│ Scorecard API   │
│ (bootstrap)     │
└─────────────────┘
```

### Data Flow — Agentic (Primary)

1. **User onboarding** captures: degree target, field, research areas, career goals, funding preference, location preferences, citizenship
2. **Profile hash** computed from user preferences
3. **Research Gateway** (Perplexity Sonar) called with structured prompts per job type
4. **Citations extracted** and quality-scored against the entity's official domain
5. **Confidence computed** and data staged in `enrichment_cache` with user_id
6. **Auto-promoted** if confidence ≥ 0.78; shown with badge if 0.55–0.77; shown with warning if <0.55
7. **User pins/saves** a school → canonical record created or updated

### Data Flow — Legacy Scraping (Fallback Only)

Scraping via Firecrawl is **disabled by default** (`ENABLE_SCRAPE_FALLBACK=false`).
It can be enabled per-request only for specific cases (e.g., "verify from official pages" feature).

---

## Prerequisites

- Python 3.11+
- Docker (PostgreSQL, Redis, MinIO, Meilisearch)
- `PERPLEXITY_API_KEY` — required for agentic research (falls back to stub provider for dev)
- `COLLEGE_SCORECARD_API_KEY` — required for foundation data load
- Optional: `SEMANTIC_SCHOLAR_API_KEY`, `OPENALEX_API_KEY` — for professor matching
- Optional: `FIRECRAWL_API_KEY` — only if scraping fallback is explicitly enabled

---

## Setup

### 1. Start services and server

```bash
docker-compose up -d
cp .env.example .env   # Edit with your keys
python run.py           # Auto-runs migrations, starts on :8000
```

### 2. Generate an internal API key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add the output to `.env` as `INTERNAL_API_KEY=<value>`.

All pipeline and ingestion endpoints accept this key via `X-Internal-Key`, alongside admin session cookie auth.

---

## Loading Foundation Data

### College Scorecard (required first step)

```bash
# All US graduate schools (async, recommended)
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"async_run": true}'

# Small batch for dev/testing
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state": "CA", "limit": 20}'
```

Foundation data populates `institutions` with IPEDS/Scorecard fields (name, city, state, type).
Enrichment (descriptions, requirements, deadlines) comes from the agentic pipeline.

---

## Agentic Research Workflows

### Flow A: Onboarding → Recommendations

The user completes onboarding, which stores their profile. The frontend then requests recommendations.

**Step 1 — User profile (set via onboarding or Settings > Application)**
```json
{
  "intended_degree": "phd",
  "primary_field_of_study": "Computer Science",
  "research_areas": ["Machine Learning", "NLP", "Computer Vision"],
  "career_goals": "Academic researcher focused on language models",
  "preferred_countries": ["USA", "Canada"],
  "funding_priority": "must_have",
  "country_of_citizenship": "US"
}
```

**Step 2 — Request recommendations**
```bash
curl -X POST http://localhost:8000/recommendations/request \
  -H "Cookie: session=<user-jwt>"

# Poll for result
curl http://localhost:8000/recommendations/latest \
  -H "Cookie: session=<user-jwt>"
```

**Step 3 — Read the result**

The response contains three tiers:
```json
{
  "status": "promoted",
  "confidence": 0.82,
  "dream": [
    {
      "school_name": "MIT",
      "location": "Cambridge, MA",
      "program_guess": "PhD in Computer Science",
      "rationale": "Strong NLP and ML labs, match with research interests",
      "confidence": 0.88,
      "citations": ["[c1] https://www.csail.mit.edu/"]
    }
  ],
  "reach_target": [...],
  "safety": [...]
}
```

**Frontend display**: The `RecommendedSchoolsTile` and `AppliedSchoolsTile` read from `GET /recommendations/latest`.

---

### Flow B: School Dossier

After a school appears in recommendations (or user finds it via search), request a detailed dossier.

**Step 1 — Find the school ID**
```bash
curl "http://localhost:8000/schools?name=MIT" \
  -H "Cookie: session=<user-jwt>"
# Note the `id` field from the response
```

**Step 2 — Request school dossier**
```bash
curl -X POST "http://localhost:8000/dossiers/schools/<school_id>/research" \
  -H "Cookie: session=<user-jwt>"
```

Response (job dispatched):
```json
{
  "job_id": "...",
  "status": "queued",
  "message": "Dossier research queued"
}
```

**Step 3 — Poll for completion**
```bash
curl "http://localhost:8000/pipeline/jobs/<job_id>" \
  -H "Cookie: session=<user-jwt>"
```

**Step 4 — Fetch the dossier value once promoted**
```bash
curl "http://localhost:8000/pipeline/cache/value?entity_kind=school_dossier&entity_id=<school_id>" \
  -H "Cookie: session=<user-jwt>"
```

The dossier includes:
- Program overview, requirements, deadlines (citation-backed)
- Official links (admissions, program page)
- Funding summary
- `confidence` score and `warnings[]` for unverified fields
- `citations_json` with source URLs and retrieval timestamps

**Frontend display**: The `InstitutionCard` and `InstitutionModal` show the dossier. The enrichment freshness badge reflects `confidence` and `fresh_until`.

---

### Flow C: Professor Matching

```bash
curl -X POST "http://localhost:8000/dossiers/schools/<school_id>/professors/match" \
  -H "Cookie: session=<user-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "research_interests": ["Machine Learning", "NLP"],
    "degree_level": "phd"
  }'
```

The system uses the user's `research_areas` from profile automatically. The `research_interests` body field is optional (overrides profile if provided).

The professor graph:
1. Queries OpenAlex for authors affiliated with the school and matching research interests (up to 5 interests, up to 25 candidates)
2. Enriches with Semantic Scholar (h-index, recent papers, citation counts)
3. Synthesises a ranked list via Perplexity with the `professor_synthesis_v1` prompt

**Read aggregated results across all saved schools**:
```bash
curl "http://localhost:8000/dossiers/professors/recommended" \
  -H "Cookie: session=<user-jwt>"
```

**Frontend display**: The `ProfessorsTile` on the dashboard reads from this endpoint.

---

### Flow D: Funding Dossier

```bash
curl -X POST "http://localhost:8000/dossiers/schools/<school_id>/funding/research" \
  -H "Cookie: session=<user-jwt>"
```

The funding dossier includes **two sections**:

**Internal funding** — institutional scholarships, TA/RA assistantships, fellowships:
```json
{
  "funding_opportunities": [
    {
      "name": "NSF Graduate Research Fellowship [c1]",
      "type": "fellowship",
      "scope": "internal",
      "amount_min": 34000,
      "amount_max": 34000,
      "covers_tuition": true,
      "covers_stipend": true,
      "eligibility_criteria": "US citizens/nationals, early-career graduate students [c2]"
    }
  ]
}
```

**External funding** — national fellowships and grants relevant to the user's field and citizenship:
```json
{
  "external_opportunities": [
    {
      "name": "NSF Graduate Research Fellowship Program [c8]",
      "funder": "National Science Foundation",
      "type": "fellowship",
      "amount_min": 37000,
      "deadline": "October annually",
      "url": "https://www.nsfgrfp.org/",
      "eligibility_note": "US citizens/nationals; early-career PhD students in STEM [c9]"
    },
    {
      "name": "Hertz Fellowship [c10]",
      "funder": "Fannie and John Hertz Foundation",
      ...
    }
  ]
}
```

The model selects external opportunities based on the user's `primary_field_of_study`, `research_areas`, and `country_of_citizenship`.

---

### Flow E: Dashboard Deadlines

Application deadlines are extracted automatically from school dossiers:

```bash
curl "http://localhost:8000/dossiers/deadlines" \
  -H "Cookie: session=<user-jwt>"
```

Returns:
```json
[
  {
    "school_name": "MIT",
    "program_name": "PhD in Computer Science",
    "deadline_date": "2026-12-15",
    "deadline_label": "Fall 2027 Application Deadline",
    "confidence": 0.91,
    "is_verified": true,
    "source_url": "https://www.eecs.mit.edu/academics/graduate/"
  }
]
```

`is_verified: false` means confidence < 0.78 — the frontend shows a "verify with school" warning.

**Frontend display**: The `CalendarTile` reads from this endpoint and computes urgency client-side.

---

## Pipeline Components

### 1. Research Gateway

Unified provider abstraction for all external research calls.

| Mode | Behavior |
|------|----------|
| **Perplexity** (`PERPLEXITY_API_KEY` set) | Real Sonar API: deep research with web access |
| **Stub** (no key) | Heuristic paths; for local development and testing |

Results cached in Redis (24h TTL, keyed by request hash).

### 2. DossierGraph (Primary enrichment)

6-node LangGraph state machine per dossier type:

```
load_dossier_context
    → research_extract        (Perplexity prompt → structured JSON)
    → validate_citations      (check citation coverage, URL quality)
    → score_dossier_confidence
    → stage_dossier           (write to enrichment_cache with user_id)
    → promote_dossier         (if confidence >= 0.78)
```

Confidence formula: `0.4 * citation_quality + 0.3 * citation_coverage + 0.3 * extraction_completeness`

| Score | Routing |
|-------|---------|
| ≥ 0.78 | Auto-promote to production tables |
| 0.55 – 0.77 | Stage only — shown with confidence badge |
| < 0.55 | Stage with "unverified" warning — no auto-repair |

**Repair is on-demand only** (admin or future paid-tier feature). This reduces LLM costs significantly.

### 3. ProfessorMatchGraph

5-node graph using academic APIs:

```
load_professor_context    (user research_areas → keyword list)
    → query_openalex      (author search, up to 25 candidates)
    → enrich_semantic_scholar  (h-index, recent papers, batch ≤ 20 @ 1 rps)
    → synthesize_rank     (Perplexity: rank by research overlap + accepting students)
    → stage_professor_matches  (enrichment_cache with user_id)
```

### 4. Source Trust Scoring

Used in `ConfidenceScorer.score_source()`:

| Source | Score | Examples |
|--------|-------|---------|
| Official entity domain | 1.0 | `mit.edu` for MIT |
| Known academic aggregators | 0.8 | usnews.com, niche.com, petersons.com, gradschools.com |
| `.edu` / `.gov` (not entity) | 0.7 | `harvard.edu` when enriching Stanford |
| General reputable | 0.5 | wikipedia.org, bloomberg.com, chronicle.com |
| Other domain | 0.3 | Any other URL |
| No URL | 0.0 | Missing citation |

### 5. Per-User Enrichment Cache

Each cache entry optionally stores a `user_id`. The lookup strategy is:

1. Try per-user entry matching `(entity_kind, entity_id, user_id, freshness_bucket)`
2. Fall back to global entry (user_id IS NULL)

This allows personalized dossiers (e.g., external funding matched to the user's citizenship and research areas) while still benefiting from shared global entries for commonly-accessed data.

### 6. Legacy LangGraph Orchestrator (Scraping, Disabled by Default)

15-node scrape pipeline: `load_context → discover_urls → fetch_page → store_raw → extract_structured → validate → score_confidence → stage_write → promote_write`

Enabled only when `ENABLE_SCRAPE_FALLBACK=true` and confidence remains below the stage threshold after agentic extraction.

---

## API Endpoints

### User Research & Dossiers (requires user session)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/recommendations/request` | Trigger AI school recommendations |
| GET | `/recommendations/latest` | Get latest recommendations for current user |
| POST | `/dossiers/schools/{id}/research` | Request school dossier |
| POST | `/dossiers/schools/{id}/professors/match` | Request professor matches |
| POST | `/dossiers/schools/{id}/funding/research` | Request funding dossier |
| GET | `/dossiers/professors/recommended` | Aggregated professor matches across saved schools |
| GET | `/dossiers/deadlines` | Upcoming deadlines from school dossiers |
| GET | `/schools/saved` | Schools researched or recommended for current user |

### Enrichment & Cache (requires user session)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/pipeline/enrich` | Enrich single entity |
| POST | `/pipeline/enrich/shortlist` | Batch enrich up to 20 entities |
| GET | `/pipeline/cache/status` | Cache freshness for entity |
| GET | `/pipeline/cache/value` | Cached dossier value |
| GET | `/pipeline/jobs/{id}` | Job status |

### Ingestion (requires `X-Internal-Key` or admin session)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ingestion/schools/scorecard/load` | Load from College Scorecard |
| POST | `/ingestion/pipeline/bulk-enrich` | Bulk LangGraph enrichment |
| GET | `/ingestion/pipeline/jobs` | List all pipeline jobs |

### Admin (requires `X-Internal-Key` or admin session)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/pipeline/admin/refresh` | Force refresh entity |
| POST | `/pipeline/admin/jobs/{id}/rerun` | Retry failed job |
| POST | `/pipeline/admin/jobs/{id}/cancel` | Cancel queued job |
| GET | `/pipeline/admin/domains` | Domain health overview |
| POST | `/pipeline/admin/cache/purge` | Purge expired cache |

---

## Cache TTLs (Freshness Buckets)

| Job Type | TTL | Key format |
|----------|-----|------------|
| `recommendation_run` | 7 days | `recommendation_run:7d` |
| `school_dossier` | 30 days | `school_dossier:30d` |
| `professor_matches` | 30 days | `professor_matches:30d` |
| `funding_dossier` | 14 days | `funding_dossier:14d` |

Manual refresh is available via `POST /pipeline/admin/refresh` or `POST /pipeline/enrich` with `force_refresh: true`.

---

## Celery Tasks & Queues

| Task | Queue | Trigger |
|------|-------|---------|
| `run_enrichment_pipeline` | `pipeline` | On-demand enrichment API |
| `run_dossier_pipeline` | `pipeline.heavy` | Dossier research API |
| `run_professor_match_pipeline` | `scholarly_api` | Professor match API |
| `purge_expired_cache` | `default` | Daily 2:00 UTC |
| `reset_domain_health` | `default` | Saturday 3:00 UTC |
| `cleanup_old_jobs` | `default` | 1st of month 4:00 UTC |

Start workers:
```bash
celery -A src.workers.celery_app worker -l info -Q default,pipeline,pipeline.heavy,scholarly_api
```

---

## Database Tables

### Production
`institutions`, `programs`, `professors`, `funding_opportunities`

### Pipeline Infrastructure
`pipeline_jobs`, `source_documents`, `raw_artifacts`, `extraction_runs`, `enrichment_cache` (with `user_id` FK), `entity_promotions`, `domain_health`

### User Data
`users`, `user_profiles` (with `research_areas` JSONB, `career_goals` TEXT), `recommendation_sessions`, `recommendation_results`

---

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLE_AGENTIC_DOSSIERS` | `true` | Use DossierGraph for school/funding/professor research |
| `ENABLE_SCRAPE_FALLBACK` | `false` | Allow Firecrawl fallback when agentic confidence is low |
| `ENABLE_BULK_SCRAPE` | `false` | Allow bulk scraping operations |

---

## Troubleshooting

**Jobs stuck in "queued"**: Celery worker not consuming the `pipeline` queue. Restart with the full queue list above.

**"Quota exceeded"**: User hit 50 enrichments/day. Admin can bypass or increase via config.

**Confidence too low**: Check `GET /pipeline/cache/value` for `warnings[]` list. Common causes: unrecognised source domain, missing citation URLs, incomplete extraction.

**"Circuit breaker open"**: Domain has too many errors. Check `GET /pipeline/admin/domains`.

**No results in professor match**: Ensure user profile has `research_areas` populated. The graph uses up to 5 interests for the OpenAlex query.

**Funding dossier missing external opportunities**: Verify `country_of_citizenship` is set in user profile — external fellowship filtering depends on it.
