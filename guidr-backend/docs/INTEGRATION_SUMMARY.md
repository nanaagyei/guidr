# Integration Summary

How all data collection, enrichment, and agentic research components work together.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENTIC CORE (primary)                     │
│                                                                     │
│  User Profile                                                       │
│  (research_areas, career_goals, citizenship, preferences)           │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────────┐   │
│  │Recommendations│  │DossierGraph     │  │ProfessorMatchGraph   │   │
│  │(Perplexity)   │  │(Perplexity +    │  │(OpenAlex + S2 +      │   │
│  │               │  │ citation check) │  │ Perplexity synth.)   │   │
│  └──────┬────────┘  └────────┬────────┘  └──────────┬───────────┘   │
│         │                   │                       │              │
│         └───────────────────┴───────────────────────┘              │
│                             │                                       │
│                             ▼                                       │
│             enrichment_cache (per-user, TTL-keyed,                  │
│                              citations_json, user_id)               │
│                             │                                       │
│                             │ confidence >= 0.78                    │
│                             ▼                                       │
│             institutions / programs / professors                    │
│             (production tables, canonical truth)                    │
└─────────────────────────────────────────────────────────────────────┘
         ▲
         │ foundation data (basic metadata)
┌────────┴──────────┐
│ College Scorecard │
│ API (bootstrap)   │
└───────────────────┘

Scraping (Firecrawl): DISABLED by default — optional fallback only
```

---

## Authentication

All pipeline-triggering endpoints use a dual-auth approach:

| Method | Header | Use case |
|--------|--------|----------|
| Internal API key | `X-Internal-Key: <key>` | Scripts, CI/CD, agents, cron jobs |
| Admin session | `Cookie: session=<jwt>` | Admin users in browser |

User-facing endpoints (`/pipeline/enrich`, `/dossiers/*`, `/recommendations/*`) require a logged-in user session cookie.

---

## Data Collection Methods

### Method 1: Foundation Load (Scorecard API)

Populates the database with basic school metadata (name, city, state, institution type).

```bash
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"async_run": true}'
```

### Method 2: Agentic Dossiers (primary enrichment)

Sends structured prompts to Perplexity for complete JSON dossiers with citation tracking.
Confidence gates data quality:

| Score | Routing |
|-------|---------|
| ≥ 0.78 | Auto-promote to production tables |
| 0.55 – 0.77 | Stage in `enrichment_cache` (shown with confidence badge) |
| < 0.55 | Stage with "unverified" warning — no auto-repair |

Repair is **on-demand only** — no automatic repair to control LLM costs.

```bash
# School dossier
curl -X POST http://localhost:8000/dossiers/schools/<id>/research \
  -H "Cookie: session=<jwt>"

# Professor matching (uses profile research_areas automatically)
curl -X POST http://localhost:8000/dossiers/schools/<id>/professors/match \
  -H "Cookie: session=<jwt>"

# Funding dossier (internal + external opportunities)
curl -X POST http://localhost:8000/dossiers/schools/<id>/funding/research \
  -H "Cookie: session=<jwt>"

# AI-powered recommendations
curl -X POST http://localhost:8000/recommendations/request \
  -H "Cookie: session=<jwt>"
```

### Method 3: Legacy LangGraph Enrichment (fallback, disabled by default)

The original Firecrawl scraping pipeline is available as a fallback.

```bash
# Only enable if ENABLE_SCRAPE_FALLBACK=true in .env
curl -X POST http://localhost:8000/ingestion/pipeline/bulk-enrich \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entity_kind": "school"}'
```

---

## Recommended Workflow

### Initial Setup (one-time)

```bash
docker-compose up -d
python run.py                   # Start server, auto-migrates

# Load foundation data
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" -H "Content-Type: application/json" \
  -d '{"async_run": true}'
```

### User Flow (per user, on-demand)

```
1. User registers → completes onboarding → profile saved
         ↓
2. POST /recommendations/request → Perplexity generates school shortlist
         ↓
3. User saves a school → POST /dossiers/schools/{id}/research
         ↓
4. Dossier staged in enrichment_cache (per-user)
   → confidence ≥ 0.78 → promoted to production
         ↓
5. POST /dossiers/schools/{id}/professors/match
   → OpenAlex + S2 → Perplexity synthesis → ranked list
         ↓
6. POST /dossiers/schools/{id}/funding/research
   → internal funding + external fellowships (field + citizenship filtered)
         ↓
7. GET /dossiers/deadlines → deadlines extracted from all dossiers
```

### Scheduled Maintenance

Celery Beat handles recurring tasks automatically:

| Schedule | Task |
|----------|------|
| Daily 2:00 UTC | Purge expired enrichment_cache entries |
| Saturday 3:00 UTC | Reset stale domain health blocks |
| 1st of month 4:00 UTC | Clean up old pipeline job records |

---

## User Profile → Research Pipeline Mapping

The user profile fields are directly consumed by the agentic pipeline:

| Profile Field | Used in |
|---------------|---------|
| `research_areas` | OpenAlex author search keywords (professor matching), recommendation prompt, funding dossier external filter |
| `primary_field_of_study` | All dossier prompts, funding dossier `field_of_study` variable |
| `career_goals` | Recommendation prompt for rationale personalisation |
| `country_of_citizenship` | External fellowship eligibility filtering (NSF, NIH, Fulbright, etc.) |
| `intended_degree` | Recommendation tier weighting, program matching |
| `funding_priority` | Recommendation prompt emphasis |
| `preferred_countries` / `preferred_cities` | Recommendation geography filtering |

Profile fields are set during onboarding and editable at **Settings → Application Settings** (Research Interests + Career Goals sections).

---

## Dashboard Data Endpoints

| Tile | API Endpoint | Data Source |
|------|-------------|-------------|
| Recommended Schools | `GET /recommendations/latest` | Latest recommendation session |
| Saved Schools | `GET /schools/saved` | Dossier cache entries + recommendation session |
| Professors | `GET /dossiers/professors/recommended` | Aggregated professor matches across saved schools |
| Upcoming Deadlines | `GET /dossiers/deadlines` | Deadline fields extracted from school dossiers |
| Profile Completion | `GET /profile` | User profile completion score |

All tiles load independently with skeleton loaders — no tile blocks another.

---

## Confidence & Source Trust

**Confidence formula (DossierGraph):**
`0.4 × citation_quality + 0.3 × citation_coverage + 0.3 × extraction_completeness`

**Source trust scoring:**

| Source | Score |
|--------|-------|
| Official entity domain (e.g., mit.edu for MIT) | 1.0 |
| Known aggregators (usnews, niche, petersons, gradschools) | 0.8 |
| `.edu` / `.gov` (not the entity's own domain) | 0.7 |
| Reputable sources (wikipedia, bloomberg, chronicle, nature) | 0.5 |
| Other URL | 0.3 |
| No URL | 0.0 |

---

## Per-User Cache

`enrichment_cache` rows carry an optional `user_id` FK (migration 017). The lookup strategy:
1. Try per-user cache entry `(entity_kind, entity_id, user_id, freshness_bucket)`
2. Fall back to global entry (user_id IS NULL)

This means:
- First user to request a dossier for MIT gets a personalised entry (their citizenship, research_areas fed into the prompt)
- A second user requesting the same school may get a new per-user entry if they have different preferences
- Global entries serve as a shared baseline if no per-user entry exists

Cache TTLs: recommendations 7 days, school dossier 30 days, professor matches 30 days, funding dossier 14 days.

---

## Error Handling & Resilience

| Concern | Mechanism |
|---------|-----------|
| Concurrent duplicate jobs | Redis dedup lock — only one job runs per fingerprint |
| API quota | Per-user Redis quota: 50 enrichments/day |
| Perplexity unavailable | Stub provider fallback (dev mode) |
| Domain blocks (scraping) | DomainHealthService circuit breaker (only relevant when scraping is enabled) |
| Inflight overload | Redis inflight semaphore caps concurrent pipeline jobs |
| Failed jobs | `retry_backoff` node re-queues with exponential delay |
| Low-confidence data | Staged with badge; no automatic LLM repair (saves cost) |

---

## Related Docs

- [Quick Start](QUICK_START.md) — Step-by-step walkthrough with curl commands
- [Pipeline Guide](PIPELINE_GUIDE.md) — Full architecture, all endpoints, DossierGraph internals
- [Enrichment Verification](ENRICHMENT_PIPELINE_VERIFICATION.md) — End-to-end smoke tests
- [R2 Setup](R2_SETUP.md) — Cloudflare R2 for production document storage
- [RFC: Agentic Research Pivot](RFC_AGENTIC_RESEARCH_PIVOT.md) — Adopted architecture decision
