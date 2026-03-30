# Comprehensive Data Collection Guide

> **Note:** The Firecrawl/scraping collection methods described in this guide are **legacy fallbacks** and are disabled by default (`ENABLE_SCRAPE_FALLBACK=false`). The primary data collection method is the **agentic research pipeline** (Perplexity Sonar + OpenAlex + Semantic Scholar). See [QUICK_START.md](QUICK_START.md) for the recommended workflow.
>
> Use this guide only if:
> - You explicitly need to collect bulk structural data via scraping (e.g., a one-time historical backfill)
> - The agentic pipeline is unavailable for a particular data type
> - You have enabled `ENABLE_SCRAPE_FALLBACK=true` in your `.env`

---

## Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium  # only needed for Playwright fallback

# Required env vars (scraping-specific)
FIRECRAWL_API_KEY=fc-your-key          # required for scraping methods
GROQ_API_KEY=gsk_your-key              # or OPENAI_API_KEY — for LLM extraction
COLLEGE_SCORECARD_API_KEY=your-key
INTERNAL_API_KEY=your-key               # for API-based collection

# Enable scraping fallback
ENABLE_SCRAPE_FALLBACK=true
```

---

## Primary Method: Agentic Research Pipeline

For the recommended approach, see [QUICK_START.md](QUICK_START.md). The full user workflow is:

```
1. Load foundation data (Scorecard API) → basic school metadata
2. User registers + sets profile (research_areas, field_of_study, citizenship, etc.)
3. POST /recommendations/request → AI school shortlist (Perplexity)
4. POST /dossiers/schools/{id}/research → full dossier per school (Perplexity)
5. POST /dossiers/schools/{id}/professors/match → professor matching (OpenAlex + S2 + Perplexity)
6. POST /dossiers/schools/{id}/funding/research → funding + external fellowships
```

---

## Legacy Scraping Methods (Fallback Only)

These methods require `ENABLE_SCRAPE_FALLBACK=true` and a valid `FIRECRAWL_API_KEY`.

### 1. Quick Start Script (3 schools)

```bash
python -m scripts.quick_start_data_collection
```

Fetches 3 top schools, collects school data, discovers programs, and shows results.

### 2. Batch Script

```bash
# 10 schools, max 15 programs each
python -m scripts.comprehensive_data_collection --max-schools 10 --max-programs 15

# 50 schools, skip already-collected
python -m scripts.comprehensive_data_collection --max-schools 50 --skip-existing
```

### 3. API-Driven Legacy Enrichment

```bash
# Load foundation data (still the correct starting point)
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state": "CA", "limit": 20}'

# Bulk scrape-enrich (legacy — requires ENABLE_SCRAPE_FALLBACK=true)
curl -X POST http://localhost:8000/ingestion/pipeline/bulk-enrich \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entity_kind": "school"}'
```

### 4. Celery Background Jobs (Legacy)

```bash
# Start worker with scraping queue
celery -A src.workers.celery_app worker -l info -Q default,scraping,processing,pipeline
```

```python
from src.workers.scraper_worker import collect_school_comprehensive_task, discover_programs_task

collect_school_comprehensive_task.delay("institution-uuid")
discover_programs_task.delay("institution-uuid")
```

---

## Components

### MultiSourceFetcher

Aggregates schools from IPEDS, rankings, and top-school lists.

```python
from src.scrapers.schools.multi_source_fetcher import MultiSourceFetcher

fetcher = MultiSourceFetcher()
schools = await fetcher.fetch_all_schools(limit=100)
```

### ComprehensiveSchoolCollector

Collects description, acceptance rate, tuition, funding from a school's website.

```python
from src.scrapers.schools.comprehensive_collector import ComprehensiveSchoolCollector

collector = ComprehensiveSchoolCollector()
data = await collector.collect_school_data("MIT", "https://www.mit.edu")
await collector.close()
```

### ProgramDiscoveryAgent

Finds graduate program URLs from a school's website.

```python
from src.scrapers.agents.program_discovery_agent import ProgramDiscoveryAgent

agent = ProgramDiscoveryAgent()
urls = await agent.discover_programs("MIT", "https://www.mit.edu")
await agent.close()
```

### ProgramCollectionAgent

Collects detailed program data from a program URL.

```python
from src.scrapers.agents.program_collection_agent import ProgramCollectionAgent

agent = ProgramCollectionAgent()
program = await agent.collect_program_data("https://mit.edu/program/cs", institution)
await agent.close()
```

---

## Legacy Collection Flow

```
MultiSourceFetcher
  └─> For each school:
      ComprehensiveSchoolCollector
        └─> Firecrawl → LLM agent → Playwright (fallback chain)
        └─> Enrich with College Scorecard
      ProgramDiscoveryAgent
        └─> Firecrawl crawl → LLM navigation → Google search (fallback chain)
      ProgramCollectionAgent (for each URL)
        └─> Firecrawl → LLM agent → Playwright (fallback chain)
        └─> Validate + save to database
```

---

## Recommended Approach

| Scale | Recommended Method | Notes |
|-------|-------------------|-------|
| Any scale (users) | **Agentic dossiers** (`POST /dossiers/schools/{id}/research`) | Per-user, on-demand, citation-backed. See [QUICK_START.md](QUICK_START.md). |
| Foundation bootstrap | College Scorecard API load | Basic school metadata only (name, city, type) |
| Historical backfill | `comprehensive_data_collection` (legacy) | Requires `ENABLE_SCRAPE_FALLBACK=true`, Firecrawl key |
| Bulk legacy enrichment | API + Celery workers | Only if agentic pipeline is unavailable |

For AI-powered research with citation tracking and confidence scoring, use the [agentic dossier system](ENRICHMENT_PIPELINE_VERIFICATION.md#10-test-agentic-dossier-system).

---

## Troubleshooting

**Scraping disabled**: If you get `ENABLE_SCRAPE_FALLBACK is false`, set `ENABLE_SCRAPE_FALLBACK=true` in your `.env`. This is intentional — the agentic pipeline is the default.

**Playwright not found**: `playwright install chromium`

**No API keys for LLM extraction**: Set `GROQ_API_KEY` or `OPENAI_API_KEY` in `.env`. These are only needed for the legacy scraping pipeline, not the agentic dossier pipeline.

**Rate limits**: The system automatically falls back to alternative methods. Reduce `SCRAPER_DELAY_SECONDS` if hitting limits.

**Memory issues with Playwright**: Process in smaller batches and ensure `await scraper.close()` is called.

**Duplicate programs**: The validator includes deduplication. Use `--skip-existing` flag.

**Better alternative**: For most use cases, the agentic dossier pipeline produces better-quality, citation-backed data with confidence scoring. See [QUICK_START.md](QUICK_START.md).

---

## Related Docs

- [Quick Start](QUICK_START.md) — Get running in 10 minutes
- [Pipeline Guide](PIPELINE_GUIDE.md) — Full pipeline architecture
- [Enrichment Verification](ENRICHMENT_PIPELINE_VERIFICATION.md) — End-to-end smoke tests
- [Integration Summary](INTEGRATION_SUMMARY.md) — How components work together
