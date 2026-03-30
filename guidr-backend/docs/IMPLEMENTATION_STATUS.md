# Guidr Backend — Implementation Status

> Last updated: 2026-03-26
> Covers Skills 17-29 + RFC Agentic Research Pivot (adopted + implemented)
> Plus: Auth hardening, pipeline internal API key, DB bootstrap, user profile research fields, per-user dossiers, external funding, updated confidence thresholds

---

## Legend


| Symbol | Meaning                                |
| ------ | -------------------------------------- |
| ✅      | Fully implemented                      |
| 🔶     | Partially implemented / has known gaps |
| ❌      | Not yet implemented                    |


---

## Skill 17 — Research Gateway

**Purpose:** Unified provider abstraction for external research (URL discovery, deep research via Perplexity Sonar API).


| Component                                      | Status | Notes                                                                                                                                           |
| ---------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `ResearchGateway` service class                | ✅      | `src/pipeline/research_gateway/service.py`                                                                                                      |
| `ResearchRequest` / `ResearchResponse` schemas | ✅      | `src/pipeline/research_gateway/schemas.py`                                                                                                      |
| `StubResearchProvider` (for dev/testing)       | ✅      | `src/pipeline/research_gateway/providers/stub.py`                                                                                               |
| `PerplexityProvider` (real Sonar API)          | ✅      | `src/pipeline/research_gateway/providers/perplexity.py`                                                                                         |
| Provider fallback when no API key              | ✅      | Auto-selects stub if `PERPLEXITY_API_KEY` not set                                                                                               |
| Redis cache for research results               | ✅      | 24h TTL, keyed by request hash                                                                                                                  |
| `source_documents` persistence after discovery | 🔶     | Service stores results in cache; `source_documents` DB row written only if model + repo wired — nodes call this but table may not be fully used |
| `OpenDeepResearchAdapter`                      | ❌      | Not implemented — Skill 17 spec mentioned this alternative provider                                                                             |
| `research_jobs` table                          | ❌      | Not created; pipeline_jobs used instead                                                                                                         |
| `research_results` / `research_cache` tables   | ❌      | Not created; enrichment_cache + Redis used instead                                                                                              |


---

## Skill 18 — LangGraph Orchestrator

**Purpose:** 15-node LangGraph state machine that drives the full fetch → extract → validate → score → promote pipeline.


| Component                             | Status | Notes                                                                  |
| ------------------------------------- | ------ | ---------------------------------------------------------------------- |
| `PipelineState` TypedDict             | ✅      | `src/pipeline/orchestrator/state.py`                                   |
| `load_context` node                   | ✅      | Queries Institution/Program from DB, loads source_documents            |
| `discover_urls` node                  | ✅      | Calls Research Gateway for URL discovery                               |
| `fetch_page` node                     | ✅      | Calls `EnhancedFirecrawlClient`, computes content SHA256               |
| `store_raw` node                      | ✅      | Stores HTML to MinIO, creates `raw_artifacts` row                      |
| `extract_structured` node             | ✅      | Dispatches to appropriate extractor (funding/faculty/program/overview) |
| `validate_payload` node               | ✅      | Calls `DataValidator` with business rules                              |
| `score_confidence` node               | ✅      | Calls `ConfidenceScorer.compute()`                                     |
| `stage_write` node                    | ✅      | Writes to `enrichment_cache`, creates `extraction_runs` row            |
| `promote_write` node                  | ✅      | Upserts to production tables, creates `entity_promotions` audit row    |
| `repair_extraction` node              | ✅      | Calls Research Gateway REPAIR_EXTRACTION job type                      |
| `retry_backoff` node                  | ✅      | Creates new pipeline_job with exponential delay                        |
| `END` edge from `stage_write`         | ✅      | Conditional: skips promote if confidence < 0.85                        |
| Graph compiled and runnable           | ✅      | `src/pipeline/orchestrator/graph.py`                                   |
| `run_enrichment_pipeline` Celery task | ✅      | `src/pipeline/tasks/orchestrator_tasks.py`                             |


---

## Skill 19 — Pipeline ORM Models

**Purpose:** SQLAlchemy models for the 8 new pipeline tables created in migration 014.


| Component                            | Status | Notes                                  |
| ------------------------------------ | ------ | -------------------------------------- |
| `PipelineJob` model                  | ✅      | `src/models/pipeline_job.py`           |
| `SourceDocument` model               | ✅      | `src/models/source_document.py`        |
| `RawArtifact` model                  | ✅      | `src/models/raw_artifact.py`           |
| `ExtractionRun` model                | ✅      | `src/models/extraction_run.py`         |
| `EntityPromotion` model              | ✅      | `src/models/entity_promotion.py`       |
| `EnrichmentCache` model              | ✅      | `src/models/enrichment_cache.py`       |
| `DomainHealth` model                 | ✅      | `src/models/domain_health.py`          |
| All models imported in `__init__.py` | ✅      | `src/models/__init__.py`               |
| `validation_reports` table / model   | ❌      | Not created — Skill 21 references this |
| `confidence_scores` table / model    | ❌      | Not created — Skill 21 references this |


---

## Skill 20 — Job Repository

**Purpose:** Repository pattern for creating, claiming, deduplicating, and completing pipeline jobs.


| Component               | Status | Notes                                                              |
| ----------------------- | ------ | ------------------------------------------------------------------ |
| `JobRepository` class   | ✅      | `src/pipeline/repositories/job_repository.py`                      |
| `compute_fingerprint()` | ✅      | SHA256 of entity_kind + entity_id + category + schema_version      |
| `create_job()`          | ✅      | With IntegrityError dedup guard                                    |
| `find_recent_success()` | ✅      | Looks back `window_hours` for COMPLETED jobs with same fingerprint |
| `claim_job()`           | ✅      | Atomic `UPDATE WHERE status='queued' → 'running'`                  |
| `complete_job()`        | ✅      | Sets status, output_json, metrics_json, timestamps                 |
| `requeue_job()`         | ✅      | Re-queues failed jobs up to max attempts                           |
| `cancel_job()`          | ✅      | Cancels queued jobs                                                |
| `list_jobs()`           | ✅      | Filter by entity_kind, entity_id, status                           |


---

## Skill 21 — Confidence Scoring

**Purpose:** Composite confidence formula; routing to promote / stage / repair based on score.


| Component                                                 | Status | Notes                                                                   |
| --------------------------------------------------------- | ------ | ----------------------------------------------------------------------- |
| `ConfidenceScorer` class                                  | ✅      | `src/pipeline/processors/confidence_scorer.py`                          |
| `score_source()` — official domain vs .edu vs other       | ✅      |                                                                         |
| `score_extraction()` — field completeness ratio           | ✅      | Per-entity expected field lists                                         |
| `score_validation()` — pass/fail + warnings               | ✅      |                                                                         |
| `score_staleness()` — freshness decay                     | ✅      | 24h=1.0, 7d=0.8, 30d=0.5, older=0.2                                     |
| `should_promote()` / `should_stage()` / `should_warn()` | ✅      | **Updated thresholds: 0.78 / 0.55** — `should_repair()` removed; repair is on-demand only |
| 5-tier source trust scoring | ✅ | 1.0=official, 0.8=aggregators, 0.7=.edu/.gov, 0.5=reputable, 0.3=other |
| `validation_reports` table                                | ❌      | Not created; validation results stored in `enrichment_cache.value_json` |
| `confidence_scores` table                                 | ❌      | Not created; confidence stored on `enrichment_cache` and `pipeline_job` |


---

## Skill 22 — Prompt Library

**Purpose:** Versioned prompt templates for URL discovery, extraction, repair, synthesis.


| Component                               | Status | Notes                                                                                                    |
| --------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------- |
| `PromptRegistry` class                  | ✅      | `src/pipeline/prompts/registry.py`                                                                       |
| `url_discovery_v1.txt` template         | ✅      | `src/pipeline/prompts/templates/url_discovery_v1.txt`                                                    |
| `repair_v1.txt` template                | ✅      | `src/pipeline/prompts/templates/repair_v1.txt`                                                           |
| `extraction_v1.txt` template            | ✅      | `src/pipeline/prompts/templates/extraction_v1.txt`                                                       |
| `synthesis_v1.txt` template             | ✅      | `src/pipeline/prompts/templates/synthesis_v1.txt` — 120-word UI-safe summary with citations              |
| `fill_missing_v1.txt` template          | ✅      | `src/pipeline/prompts/templates/fill_missing_v1.txt` — fills only missing fields from partial extraction |
| Prompt versioning / A/B testing support | ❌      | Registry loads by name only; no version selection logic                                                  |


---

## Skill 23 — Enrichment API + Service

**Purpose:** User-facing REST API for triggering on-demand enrichment, polling job status, and reading cache freshness.


| Component                                     | Status | Notes                                                                            |
| --------------------------------------------- | ------ | -------------------------------------------------------------------------------- |
| `EnrichmentService` class                     | ✅      | `src/services/enrichment_service.py`                                             |
| Cache-first lookup                            | ✅      | Returns cached data if within staleness window                                   |
| Per-user Redis quota check                    | ✅      | 50 enrichments/user/day                                                          |
| Dedup via Redis lock                          | ✅      | Prevents duplicate jobs for same fingerprint                                     |
| Job dispatch to Celery (orchestrator task)    | ✅      | `run_enrichment_pipeline.delay(job_id)`                                          |
| `POST /pipeline/enrich`                       | ✅      | `src/routes/pipeline.py`                                                         |
| `POST /pipeline/enrich/shortlist`             | ✅      | Batch up to 20 items                                                             |
| `GET /pipeline/cache/status`                  | ✅      |                                                                                  |
| `GET /pipeline/cache/value`                   | ✅      |                                                                                  |
| `GET /pipeline/jobs/{job_id}`                 | ✅      |                                                                                  |
| Pipeline router registered in `main.py`       | ✅      | `app.include_router(pipeline.router)`                                            |
| `last_enriched_at` column on canonical tables | ✅      | Added to Institution, Program, Professor, FundingOpportunity via migration 015   |
| `last_enrichment_confidence` column           | ✅      | Added to all 4 canonical tables via migration 015                                |
| `data_version` column                         | ✅      | Added to all 4 canonical tables; incremented on each promote_write               |
| Enrichment metadata in entity GET responses   | ✅      | InstitutionResponse schema + programs list response include enrichment fields    |
| `POST /ingestion/pipeline/bulk-enrich`        | ✅      | Queues LangGraph enrichment jobs for all entities of given kind with cache dedup |
| `scripts/reset_data.py`                       | ✅      | Full pipeline + canonical data reset with --dry-run and --yes flags              |


---

## Skill 24 — Admin Endpoints

**Purpose:** Admin-only pipeline management: force-refresh, rerun, cancel, domain health, cache purge.


| Component                               | Status | Notes                         |
| --------------------------------------- | ------ | ----------------------------- |
| `POST /pipeline/admin/refresh`          | ✅      |                               |
| `POST /pipeline/admin/jobs/{id}/rerun`  | ✅      |                               |
| `POST /pipeline/admin/jobs/{id}/cancel` | ✅      |                               |
| `GET /pipeline/admin/domains`           | ✅      |                               |
| `POST /pipeline/admin/cache/purge`      | ✅      |                               |
| `require_admin_user` dependency         | ✅      | All admin endpoints protected |


---

## Skill 25 — Redis Keyspace + Rate Limiting

**Purpose:** Token bucket rate limiting, quota enforcement, circuit breakers, dedup locks.


| Component                                          | Status | Notes                                                                                       |
| -------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------- |
| `redis_keyspace/keys.py` — key generators          | ✅      | User quota, circuit breaker, dedup lock keys                                                |
| `redis_keyspace/rate_limit.py` — token bucket      | ✅      | Per-domain rate limiting                                                                    |
| `redis_keyspace/quota.py` — user quota             | ✅      | Lua-based atomic `CHECK_QUOTA` script                                                       |
| `redis_keyspace/lua_scripts.py` — Lua scripts      | ✅      | TOKEN_BUCKET + CHECK_QUOTA                                                                  |
| Circuit breaker (`is_blocked` / `record_error`)    | ✅      | In `rate_limit.py`                                                                          |
| Per-endpoint HTTP rate limiting middleware         | ❌      | No FastAPI middleware/dependency for request-level rate limits (e.g., 100 req/min per user) |
| Global inflight cap (max concurrent pipeline jobs) | ❌      | Not implemented; Celery concurrency is the only limit                                       |


---

## Skill 26 — Domain Health Service

**Purpose:** Track per-domain error rates, auto-block misbehaving domains, surface in admin dashboard.


| Component                                      | Status | Notes                                                                                                     |
| ---------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------- |
| `DomainHealthService` class                    | ✅      | `src/pipeline/services/domain_health_service.py`                                                          |
| `record_success(host)`                         | ✅      | Resets Redis error streak                                                                                 |
| `record_error(host, http_status)`              | ✅      | Increments streak; writes `domain_health` DB row                                                          |
| `is_blocked(host)`                             | ✅      | Checks Redis circuit breaker + DB block flag                                                              |
| `get_all_health()`                             | ✅      | Admin dashboard data                                                                                      |
| `reset_stale_blocks()`                         | ✅      | Clears domains blocked > 7 days                                                                           |
| Domain check integrated into `fetch_page` node | ✅      | `fetch_page` calls `is_blocked()` before fetch; `record_success()` / `record_error()` after — fully wired |


---

## Skill 27 — Maintenance Tasks + Worker Specialization

**Purpose:** Scheduled cleanup tasks and Celery worker configuration.


| Component                                                      | Status | Notes                                                                                                      |
| -------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| `purge_expired_cache` task (daily 2 AM)                        | ✅      | `src/pipeline/tasks/maintenance_tasks.py`                                                                  |
| `reset_domain_health` task (weekly Sat 3 AM)                   | ✅      |                                                                                                            |
| `cleanup_old_jobs` task (monthly 1st 4 AM)                     | ✅      |                                                                                                            |
| Beat schedules registered                                      | ✅      | `src/pipeline/tasks/scheduled_tasks.py`                                                                    |
| Default Celery worker handles all queues (dev)                 | ✅      | `docker-compose.yml`                                                                                       |
| Dedicated `celery-worker-pipeline` (prod profile)              | ✅      | `docker-compose.yml` `profiles: [production]`                                                              |
| Priority queue routing (`pipeline.critical`, `.high`, `.bulk`) | 🔶     | Queue names defined in `celery_app.py` routing; Celery priority within a queue not configured              |
| Exponential backoff retry policy on pipeline tasks             | 🔶     | `retry_backoff` orchestrator node creates new jobs with delay; Celery-level `autoretry_for` not configured |
| Worker concurrency / time limits per type                      | ❌      | Single concurrency setting; no per-worker-type tuning                                                      |


---

## Skill 28 — Tests

**Purpose:** Comprehensive test coverage for all pipeline components.


| Component                    | Status | Notes       |
| ---------------------------- | ------ | ----------- |
| `test_job_repository.py`     | ❌      | Not written |
| `test_redis_primitives.py`   | ❌      | Not written |
| `test_enrichment_service.py` | ❌      | Not written |
| `test_pipeline_api.py`       | ❌      | Not written |
| `test_confidence_scorer.py`  | ✅      | Written — covers updated thresholds (0.78/0.55), 5-tier source scoring, should_warn |
| `test_orchestrator_nodes.py` | ❌      | Not written |
| `test_orchestrator_e2e.py`   | ❌      | Not written |
| `test_research_gateway.py`   | ❌      | Not written |
| `test_domain_health.py`      | ❌      | Not written |
| `test_maintenance_tasks.py`  | ❌      | Not written |


> **Note:** `test_confidence_scorer.py` is now written. The remaining 9 test files cover legacy scraping pipeline components; they are still missing but lower priority given the agentic pivot.

---

## Summary


| Phase                                 | Status         | Key Gaps                                                                          |
| ------------------------------------- | -------------- | --------------------------------------------------------------------------------- |
| **Skill 17** — Research Gateway       | 🔶 Mostly done | No `OpenDeepResearchAdapter`; research DB tables not created                      |
| **Skill 18** — LangGraph Orchestrator | ✅ Complete     | —                                                                                 |
| **Skill 19** — Pipeline ORM Models    | 🔶 Mostly done | `validation_reports` and `confidence_scores` tables missing                       |
| **Skill 20** — Job Repository         | ✅ Complete     | —                                                                                 |
| **Skill 21** — Confidence Scoring     | 🔶 Mostly done | Validation/confidence not persisted to dedicated tables                           |
| **Skill 22** — Prompt Library         | ✅ Complete     | All 5 templates exist; A/B versioning is a future enhancement                     |
| **Skill 23** — Enrichment API         | ✅ Complete     | Enrichment columns added; bulk-enrich endpoint added; reset script added          |
| **Skill 24** — Admin Endpoints        | ✅ Complete     | —                                                                                 |
| **Skill 25** — Redis Keyspace         | 🔶 Mostly done | No per-endpoint HTTP rate limit middleware; no global inflight cap                |
| **Skill 26** — Domain Health          | ✅ Complete     | `fetch_page` fully wires `DomainHealthService` — blocks, records errors/successes |
| **Skill 27** — Maintenance + Workers  | 🔶 Mostly done | Worker concurrency/time limits not tuned; Celery autoretry not configured         |
| **Skill 28** — Tests                  | ❌ Not started  | All 10 test files missing                                                         |


### Priority Next Steps

1. **Run the data pipeline** — execute `scripts/reset_data.py` → load scorecard → `POST /ingestion/pipeline/bulk-enrich` to populate institutions + programs
2. **Add per-endpoint rate limiting middleware** (Skill 25) — public pipeline endpoints have no HTTP-level throttling
3. **Add `validation_reports` and `confidence_scores` tables** (Skill 19/21) — currently stored in enrichment_cache JSONB only
4. **Add `OpenDeepResearchAdapter`** (Skill 17) — alternative deep-research provider for when Perplexity is unavailable
5. **Write legacy pipeline tests** (Skill 28) — start with `test_confidence_scorer.py` and `test_job_repository.py` as they have no external dependencies

---

## Skill 29 — Agentic Dossier System

> Added: 2026-03-04 | Updated: 2026-03-26 (RFC pivot adopted)
>
> **Purpose:** Agent-first enrichment pipeline that sends structured prompts to Perplexity for complete JSON dossiers with citation tracking. Adds school dossiers, professor matching (OpenAlex + Semantic Scholar), funding dossiers (internal + external), and Perplexity-powered recommendations. Scraping is disabled by default; it is an optional fallback only.
>
> **RFC Agentic Research Pivot — Adopted decisions:**
> - External funding opportunities included in v1 alongside school-specific funding
> - Broader trusted domain policy: 1.0 / 0.8 / 0.7 / 0.5 / 0.3 tiers
> - Per-user enrichment_cache entries (user_id FK in migration 017)
> - Confidence thresholds: promote ≥0.78, stage 0.55–0.77, warn <0.55; no auto-repair

### Phase 1: Database Migration (016)


| Component                                                               | Status | Notes                                    |
| ----------------------------------------------------------------------- | ------ | ---------------------------------------- |
| `016_dossier_system.py` migration                                       | ✅      | `alembic/versions/016_dossier_system.py` |
| `extraction_runs.evidence_map_json` JSONB column                        | ✅      |                                          |
| `professors.openalex_id` / `semantic_scholar_id` / `orcid_id` (indexed) | ✅      |                                          |
| `enrichment_cache.citations_json` / `evidence_map_json` JSONB           | ✅      |                                          |
| `recommendation_sessions.pipeline_job_id` FK + `citations_json`         | ✅      |                                          |
| `recommendation_results.citations_json` / `evidence_map_json`           | ✅      |                                          |


### Phase 2: Config & Feature Flags


| Component                                             | Status | Notes           |
| ----------------------------------------------------- | ------ | --------------- |
| `enable_agentic_dossiers` flag                        | ✅      | `src/config.py` |
| `enable_scrape_fallback` flag                         | ✅      |                 |
| `enable_bulk_scrape` flag                             | ✅      |                 |
| `semantic_scholar_api_key` / `openalex_api_key`       | ✅      |                 |
| `semantic_scholar_rps` / `openalex_rps` rate settings | ✅      |                 |


### Phase 3: Research Gateway Upgrades


| Component                                            | Status | Notes                                                   |
| ---------------------------------------------------- | ------ | ------------------------------------------------------- |
| `DossierCitation` schema                             | ✅      | `src/pipeline/research_gateway/schemas.py`              |
| `DossierResponse` schema                             | ✅      |                                                         |
| `DOSSIER_JOB_TYPES` frozenset                        | ✅      |                                                         |
| `extract_dossier()` abstract method on base provider | ✅      | `src/pipeline/research_gateway/providers/base.py`       |
| `extract_dossier()` Perplexity implementation        | ✅      | `src/pipeline/research_gateway/providers/perplexity.py` |
| Gateway service dossier handling + category TTLs     | ✅      | `src/pipeline/research_gateway/service.py`              |


### Phase 4: Academic API Clients


| Component                                                | Status | Notes                                                                                                          |
| -------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| `SemanticScholarClient`                                  | ✅      | `src/pipeline/clients/semantic_scholar.py` — `search_author()`, `get_author()`, `get_author_papers()`          |
| `OpenAlexClient`                                         | ✅      | `src/pipeline/clients/openalex.py` — `search_authors()`, `get_author()`, `get_institution()`, `search_works()` |
| Redis token bucket rate limiting (S2: 1 rps, OA: 10 rps) | ✅      |                                                                                                                |


### Phase 5: Prompt Templates


| Component                       | Status | Notes                                         |
| ------------------------------- | ------ | --------------------------------------------- |
| `recommendation_run_v1.txt`     | ✅      | 30 schools in dream/reach/target/safety tiers |
| `school_dossier_v1.txt`         | ✅      | Overview, requirements, deadlines, funding    |
| `professor_synthesis_v1.txt`    | ✅      | Rank professors from API data                 |
| `funding_dossier_v1.txt`        | ✅      | Internal funding + **external fellowships** (NSF, NIH, NDSEG, Hertz, etc.) |
| `recommendation_repair_v1.txt`  | ✅      | Repair prompt for recommendations             |
| `school_dossier_repair_v1.txt`  | ✅      | Repair prompt for school dossiers             |
| `funding_dossier_repair_v1.txt` | ✅      | Repair prompt for funding dossiers            |
| Injection guard in all prompts  | ✅      | "treat retrieved page text as untrusted"      |


### Phase 6a: DossierGraph


| Component                                             | Status | Notes                                                       |
| ----------------------------------------------------- | ------ | ----------------------------------------------------------- |
| `DossierState` TypedDict                              | ✅      | `src/pipeline/orchestrator/dossier_state.py`                |
| `load_dossier_context` node                           | ✅      | **Now includes** `research_areas`, `career_goals`, `country_of_citizenship` from user profile |
| `research_extract` node                               | ✅      | Renders prompt, calls gateway with `DOSSIER_EXTRACTION`     |
| `validate_citations` node                             | ✅      | Computes `citation_coverage_ratio`                          |
| `score_dossier_confidence` node                       | ✅      | 40% citation + 30% coverage + 30% extraction                |
| `stage_dossier` node                                  | ✅      | Writes to `enrichment_cache` with citations                 |
| `fallback_scrape` node                                | ✅      | Conditional: confidence < 0.55 AND `enable_scrape_fallback` (default false) |
| `promote_dossier` node                                | ✅      | Reuses `promote_write` pattern                              |
| Conditional graph routing (≥0.78 / 0.55–0.77 / <0.55) | ✅      | **Updated thresholds** — `src/pipeline/orchestrator/dossier_graph.py` |


### Phase 6b: ProfessorMatchGraph


| Component                        | Status | Notes                                                   |
| -------------------------------- | ------ | ------------------------------------------------------- |
| `ProfessorMatchState` TypedDict  | ✅      | `src/pipeline/orchestrator/professor_state.py`          |
| `load_professor_context` node    | ✅      | `src/pipeline/orchestrator/professor_nodes.py`          |
| `query_openalex` node            | ✅      | Searches authors by affiliation + keywords (up to 25)   |
| `enrich_semantic_scholar` node   | ✅      | h-index, recent papers (batch ≤ 20, 1 rps)              |
| `synthesize_rank` node           | ✅      | Perplexity synthesis with professor_synthesis_v1 prompt |
| `stage_professor_matches` node   | ✅      | Writes to `enrichment_cache`, upserts professor IDs     |
| `promote_professor_matches` node | ✅      | Creates/updates `professors` rows                       |
| Linear graph flow                | ✅      | `src/pipeline/orchestrator/professor_graph.py`          |


### Phase 7: Service Layer & Celery Tasks


| Component                                  | Status | Notes                                                            |
| ------------------------------------------ | ------ | ---------------------------------------------------------------- |
| `run_dossier_pipeline` Celery task         | ✅      | `src/pipeline/tasks/dossier_tasks.py`                            |
| `run_professor_match_pipeline` Celery task | ✅      |                                                                  |
| `DossierService` class                     | ✅      | `src/services/dossier_service.py`                                |
| `request_school_dossier()`                 | ✅      | Cache → quota → dedup → dispatch                                 |
| `request_funding_dossier()`                | ✅      |                                                                  |
| `request_professor_matches()`              | ✅      |                                                                  |
| `request_recommendations()`                | ✅      |                                                                  |
| `EnrichmentService` dossier routing        | ✅      | `src/services/enrichment_service.py` — routes to `dossier_tasks` |
| Celery queue routing for new tasks         | ✅      | `src/workers/celery_app.py`                                      |


### Phase 8: API Routes


| Component                                      | Status | Notes                            |
| ---------------------------------------------- | ------ | -------------------------------- |
| `POST /dossiers/schools/{id}/research`         | ✅      | `src/routes/dossiers.py`         |
| `POST /dossiers/schools/{id}/professors/match` | ✅      |                                  |
| `POST /dossiers/schools/{id}/funding/research` | ✅      |                                  |
| `POST /recommendations/run`                    | ✅      | `src/routes/recommendations.py`  |
| Pydantic schemas                               | ✅      | `src/schemas/dossier_schemas.py` |
| Router registered in `main.py`                 | ✅      |                                  |


### Phase 9: Tests


| Component                              | Status | Notes                                            |
| -------------------------------------- | ------ | ------------------------------------------------ |
| `test_academic_clients.py` (9 tests)   | ✅      | SemanticScholarClient + OpenAlexClient           |
| `test_dossier_nodes.py` (9 tests)      | ✅      | Each dossier node with mocked providers          |
| `test_professor_nodes.py` (7 tests)    | ✅      | OpenAlex/S2 nodes with mocked APIs               |
| `test_dossier_service.py` (7 tests)    | ✅      | Cache hit, quota, dedup, dispatch, force refresh |
| `test_dossier_graph_e2e.py` (2 tests)  | ✅      | Full DossierGraph with stub provider             |
| `test_professor_graph_e2e.py` (1 test) | ✅      | Full ProfessorMatchGraph with mocked APIs        |
| `test_dossier_routes.py` (4 tests)     | ✅      | Authenticated endpoint tests                     |



---

## Auth & Security Hardening (2026-03-26)

**Purpose:** Fix sign-in failures, scope email 2FA to signup-only, implement 30-day remember-me, and add internal API key auth for pipeline/ingestion endpoints.


| Component                                     | Status | Notes                                                                                       |
| --------------------------------------------- | ------ | ------------------------------------------------------------------------------------------- |
| Auto-run Alembic migrations on startup        | ✅      | `run.py` calls `alembic upgrade head` before uvicorn start                                  |
| `ProgrammingError` handled in `check-email`   | ✅      | Returns 503 instead of 500 when tables are missing                                          |
| Login without email 2FA code                  | ✅      | `POST /auth/login` accepts email + password only; `verification_code` removed from schema   |
| 2FA code restricted to register/password_reset | ✅      | `POST /auth/2fa/send` rejects `purpose="login"`                                             |
| Remember-me 30-day persistence                | ✅      | JWT `exp` and cookie `max_age` both set to 30 days when `remember_me=True`                  |
| Default session: 24-hour token                | ✅      | Non-remember login gets 24h JWT (was 7 days); session-scoped cookie                         |
| `create_access_token` accepts `expires_delta`  | ✅      | `src/utils/jwt.py` — parameterized expiry instead of hardcoded 7 days                       |
| Email service: granular SMTP error handling   | ✅      | Separate handling for `SMTPAuthenticationError`, `SMTPConnectError`                          |
| Internal API key config setting               | ✅      | `INTERNAL_API_KEY` in `src/config.py` and `.env.example`                                    |
| `require_internal_api_key` dependency         | ✅      | `src/dependencies/auth.py` — validates `X-Internal-Key` header                              |
| `require_admin_or_internal_key` dependency    | ✅      | Accepts either admin session cookie OR internal API key for pipeline/ingestion routes        |
| Pipeline admin endpoints accept API key       | ✅      | `src/routes/pipeline.py` — admin endpoints use `require_admin_or_internal_key`               |
| Ingestion endpoints accept API key            | ✅      | `src/routes/data_ingestion.py` — all endpoints use `require_admin_or_internal_key`           |
| Frontend login simplified (no 2FA step)       | ✅      | `guidr-frontend/src/app/auth/login/page.tsx` — direct email+password submit                 |
| Frontend API types updated                    | ✅      | `postLogin` no longer requires `verification_code`; `send2FACode` purpose types narrowed    |


---

## Updated Summary


| Phase                                  | Status         | Key Gaps                                                     |
| -------------------------------------- | -------------- | ------------------------------------------------------------ |
| **Skill 17** — Research Gateway        | 🔶 Mostly done | No `OpenDeepResearchAdapter`; research DB tables not created |
| **Skill 18** — LangGraph Orchestrator  | ✅ Complete     | —                                                            |
| **Skill 19** — Pipeline ORM Models     | 🔶 Mostly done | `validation_reports` and `confidence_scores` tables missing  |
| **Skill 20** — Job Repository          | ✅ Complete     | —                                                            |
| **Skill 21** — Confidence Scoring      | 🔶 Mostly done | Validation/confidence not persisted to dedicated tables      |
| **Skill 22** — Prompt Library          | ✅ Complete     | All 5 templates + 7 dossier templates exist                  |
| **Skill 23** — Enrichment API          | ✅ Complete     | —                                                            |
| **Skill 24** — Admin Endpoints         | ✅ Complete     | Now accepts internal API key alongside admin session         |
| **Skill 25** — Redis Keyspace          | 🔶 Mostly done | No per-endpoint HTTP rate limit middleware                   |
| **Skill 26** — Domain Health           | ✅ Complete     | —                                                            |
| **Skill 27** — Maintenance + Workers   | 🔶 Mostly done | Worker concurrency/time limits not tuned                     |
| **Skill 28** — Tests (Legacy Pipeline) | ❌ Not started  | 10 legacy pipeline test files missing                        |
| **Skill 29** — Agentic Dossier System  | ✅ Complete     | All 9 phases implemented with 39 tests                       |


