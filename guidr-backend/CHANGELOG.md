# CHANGELOG

All notable changes to Guidr Backend will be documented in this file.

## [Unreleased]

### Added
- [2026-02-18 UTC] chore(git): Comprehensive .gitignore for GitHub push readiness
  - Root .gitignore: env/secrets, Python, Node, IDE, OS, project-specific (ai_prompt_files, CLAUDE.md, logos)
  - Backend: env variants, *.pem/*.key, mypy/ruff cache, IPEDS data files
  - Frontend: env variants, pnpm-store, IDE files
  - Files: `.gitignore`, `guidr-backend/.gitignore`, `guidr-frontend/.gitignore`

- [2026-02-19 UTC] docs(pipeline): Enrichment Pipeline Verification & Operations Guide
  - Complete setup, verification, and operations documentation for the enrichment pipeline
  - Covers: LangGraph orchestrator usage (direct and via Celery), enrichment API (all endpoints with curl examples), Perplexity Research Gateway (stub vs real provider testing), confidence scoring formula and threshold verification, job/cache/artifact monitoring, admin operations, Celery worker setup (dev vs production), scheduled maintenance tasks, end-to-end smoke test (10-step walkthrough), troubleshooting for common issues (circuit breakers, quota, URL discovery failures)
  - Updated .env.example with PERPLEXITY_API_KEY and RESEARCH_MAX_CONCURRENT
  - Files: `docs/ENRICHMENT_PIPELINE_VERIFICATION.md`, `.env.example`

- [2026-02-19 UTC] feat(pipeline): Phase 1-4 pipeline integration
  - Phase 1: 7 SQLAlchemy ORM models (PipelineJob, SourceDocument, RawArtifact, ExtractionRun, EntityPromotion, EnrichmentCache, DomainHealth), JobRepository, Redis quota enforcement with Lua scripts, circuit breaker
  - Phase 2: Enrichment API (POST /pipeline/enrich, batch shortlist, cache status/value, job polling), EnrichmentService with staleness windows, enrichment metadata on entity detail responses, frontend useEnrichment hook + EnrichmentBadge component
  - Phase 3: ConfidenceScorer (0.35*source + 0.35*extraction + 0.25*validation + 0.05*staleness), real orchestrator node implementations replacing stubs, orchestrator Celery task, PromptRegistry with versioned templates, real Perplexity Sonar provider, conditional auto-promote/stage graph edge
  - Phase 4: DomainHealthService (Redis + Postgres dual-path), maintenance Celery tasks (purge cache, reset domains, cleanup old jobs), Beat schedule for maintenance, specialized pipeline worker in docker-compose
  - Files: `src/models/pipeline_job.py`, `src/models/source_document.py`, `src/models/raw_artifact.py`, `src/models/extraction_run.py`, `src/models/entity_promotion.py`, `src/models/enrichment_cache.py`, `src/models/domain_health.py`, `src/pipeline/repositories/job_repository.py`, `src/pipeline/redis_keyspace/quota.py`, `src/pipeline/schemas/enrichment_schemas.py`, `src/services/enrichment_service.py`, `src/routes/pipeline.py`, `src/pipeline/processors/confidence_scorer.py`, `src/pipeline/tasks/orchestrator_tasks.py`, `src/pipeline/prompts/registry.py`, `src/pipeline/research_gateway/providers/perplexity.py`, `src/pipeline/services/domain_health_service.py`, `src/pipeline/tasks/maintenance_tasks.py`

### Changed
- [2026-02-19 UTC] refactor(pipeline): Updated existing files for pipeline integration
  - `src/models/__init__.py`: Added 7 new model imports
  - `src/config.py`: Added perplexity_api_key, research_max_concurrent
  - `src/main.py`: Registered pipeline router
  - `src/routes/schools.py`: Added detail endpoint + enrichment metadata
  - `src/routes/programs.py`: Added enrichment metadata to detail response
  - `src/routes/professors.py`: Added enrichment metadata to detail response
  - `src/routes/funding.py`: Added enrichment metadata to detail response
  - `src/pipeline/orchestrator/nodes.py`: Replaced all stub nodes with real implementations
  - `src/pipeline/orchestrator/state.py`: Added pipeline_job_id, source_document_id, extraction_run_id, fetched_at, content_hash fields
  - `src/pipeline/orchestrator/graph.py`: Added conditional stage_decision edge
  - `src/pipeline/processors/validator.py`: Added validate_generic dispatcher
  - `src/pipeline/research_gateway/service.py`: Provider auto-selection, Redis caching, source_documents persistence
  - `src/pipeline/redis_keyspace/lua_scripts.py`: Added CHECK_QUOTA Lua script
  - `src/pipeline/redis_keyspace/keys.py`: Added circuit_breaker_key, domain_error_streak_key
  - `src/pipeline/redis_keyspace/rate_limit.py`: Added circuit breaker functions
  - `src/workers/celery_app.py`: Added maintenance tasks include, pipeline queue routing
  - `src/pipeline/tasks/scheduled_tasks.py`: Added maintenance Beat schedules
  - `docker-compose.yml`: Added celery-worker-pipeline service (production profile), default worker consumes pipeline queue in dev
  - `guidr-frontend/src/utils/api.ts`: Added enrichment API functions
  - `guidr-frontend/src/app/programs/[id]/page.tsx`: Added EnrichmentBadge
  - `guidr-frontend/src/components/InstitutionModal.tsx`: Added EnrichmentBadge

### Fixed
- [2026-02-18 UTC] fix(migration): Use create_type=False for sa.Enum in 014_pipeline_tables_v2
  - Avoids DuplicateObject error when enums already created by DO $$ blocks
  - Affects pipeline_jobs, raw_artifacts, extraction_runs, entity_promotions, enrichment_cache
  - Files: `alembic/versions/014_pipeline_tables_v2.py`

### Added
- [2026-02-18 UTC] feat(scripts): reset_pipeline_data.py for full pipeline data wipe
  - Deletes institutions, programs, professors, funding, scrape_jobs in FK-safe order
  - Preserves users, profiles, recommendation sessions; nullifies essay target_program_id
  - Clears Meilisearch indexes; supports --dry-run and --yes flags
  - Files: `scripts/reset_pipeline_data.py`

- [2026-02-18 UTC] feat(scripts): load_scorecard_schools.py CLI for College Scorecard bulk load
  - Loads all US graduate schools via College Scorecard API (degrees_awarded.highest 3..4)
  - Supports --state and --limit; Celery task ingestion.load_scorecard_schools already wired
  - COLLEGE_SCORECARD_API_KEY documented in .env.example
  - Files: `scripts/load_scorecard_schools.py`

- [2026-02-18 UTC] feat(pipeline): Pipeline tables migration (014)
  - Enums: job_status, job_priority, artifact_type, extraction_status, entity_kind, research_provider
  - Tables: source_documents, pipeline_jobs, raw_artifacts, extraction_runs, entity_promotions, enrichment_cache, recommendation_cache, domain_health
  - Files: `alembic/versions/014_pipeline_tables_v2.py`

- [2026-02-18 UTC] feat(pipeline): Redis keyspace for dedup and rate limiting
  - Fingerprint computation, acquire/release lock, token bucket rate limiter, quota_increment
  - Lua scripts for atomic operations; key builders per guidr:v1 prefix
  - Files: `src/pipeline/redis_keyspace/`

- [2026-02-18 UTC] feat(pipeline): Research Gateway service
  - POST /internal/research/run for URL_DISCOVERY, REPAIR_EXTRACTION
  - PerplexityStubProvider with heuristic URL discovery from website_hint
  - Files: `src/pipeline/research_gateway/`, `src/routes/research.py`

- [2026-02-18 UTC] feat(pipeline): LangGraph orchestrator
  - State machine: load_context -> discover -> fetch -> extract -> validate -> promote
  - Repair loop for low-confidence extraction; Celery task pipeline.run_orchestrator
  - Files: `src/pipeline/orchestrator/`, `langgraph` in requirements.txt
- [2025-02-03 UTC] feat(auth): \"Keep me signed in\" support and graceful DB errors
  - UserLogin schema now accepts remember_me; login endpoint sets a 30-day session cookie when enabled
  - Added OperationalError handling in auth routes so database outages return a friendly 503 instead of a raw 500
  - Files: `src/schemas/auth.py`, `src/routes/auth.py`

- [2025-02-03 UTC] feat(email): Guidr logo and no-reply sender in 2FA/password-reset emails
  - 2FA and password-reset emails now include Guidr logo (img from APP_PUBLIC_URL/images/guidr-logo.png)
  - Default email_from changed to "Guidr <no-reply@guidr.app>"; configurable via EMAIL_FROM
  - Added APP_PUBLIC_URL config (default https://guidr.app) for logo URL in emails
  - Files: `src/config.py`, `src/services/email.py`, `.env.example`

- [2026-02-02 21:00 UTC] feat(search): Meilisearch index configuration for all entities (Skill 11)
  - Added FUNDING_INDEX constant, search_funding(), serialize_funding(), index_funding(), batch_index_funding(), delete_funding() to SearchService
  - Configured filterable/sortable attributes for all three indexes:
    - Institutions: filterable (country, state_or_province, institution_type, public_private), sortable (name, data_completeness_score)
    - Programs: filterable (degree_level, field_of_study, institution_name, institution_country), sortable (name, tuition_estimate_per_year, application_deadline_primary)
    - Funding: filterable (funding_type, covers_tuition, covers_stipend, is_need_based, is_merit_based, institution_country, institution_id), sortable (name, amount_min, amount_max, deadline)
  - Updated ensure_indexes() and clear_all_indexes() to include funding
  - Added explicit task exports to pipeline/tasks/__init__.py
  - Files: `src/services/search_service.py`, `src/pipeline/tasks/__init__.py`

- [2026-02-02 21:00 UTC] feat(api): Funding opportunity API endpoints (Skill 10)
  - GET `/funding` - list with filters (institution_id, funding_type, covers_tuition, keyword, country, amount range) and Meilisearch fallback
  - GET `/funding/{funding_id}` - detailed funding view
  - GET `/funding/institution/{institution_id}` - list all for institution
  - Registered funding router in main app
  - Files: `src/routes/funding.py`, `src/main.py`

### Changed
- [2025-02-03 UTC] fix(email): Display sender as no-reply@guidr.app instead of personal Gmail
  - email_from default updated from nanakwameagyeituffour@gmail.com to Guidr <no-reply@guidr.app>
  - Files: `src/config.py`

- [2026-02-02 21:00 UTC] fix(api): Fix N+1 query in funding routes
  - Added `contains_eager` / `joinedload` to funding list and detail endpoints
  - Files: `src/routes/funding.py`

- [2026-02-02 21:00 UTC] refactor(ingestion): Add funding to reindex_search
  - reindex_search() now indexes funding opportunities alongside institutions and programs
  - Files: `src/services/data_ingestion.py`

- [2026-02-02 21:00 UTC] chore(config): Update .env.example with pipeline variables
  - Added Google Search, Playwright, pipeline settings, agent settings
  - Files: `.env.example`

- [2026-02-02 19:00 UTC] feat(pipeline): Scraping orchestrator (Phase 4)
  - Added ScrapingOrchestrator with discover_graduate_pages()
  - Centralized robots check and URL categorization (overview, programs, faculty, funding)
  - Firecrawl client accepts pre_discovered_urls for orchestrator integration
  - Files: `src/pipeline/scraping/orchestrator.py`, `src/pipeline/clients/firecrawl_enhanced.py`

- [2026-02-02 19:00 UTC] feat(pipeline): Staging layer and processors (Phase 5)
  - Added staging schema and staging_records table
  - Added DataValidator, DataTransformer, DataEnricher processors
  - Files: `src/pipeline/processors/`, `alembic/versions/013_staging_schema_and_schema_alignment.py`

- [2026-02-02 19:00 UTC] feat(models): Schema alignment (Phase 6)
  - Added program_id to FundingOpportunity
  - Created ProfessorProgram association table
  - Files: `src/models/funding_opportunity.py`, `src/models/professor_program.py`

- [2026-02-02 19:00 UTC] docs: Pipeline and backend documentation
  - Added docs/PIPELINE_GUIDE.md (architecture, setup, API, troubleshooting)
  - Updated README with pipeline section and project structure
  - Updated QUICK_START.md with pipeline steps
  - Added scripts/verify_pipeline_setup.py
  - Updated .env.example with pipeline/MinIO vars

- [2026-02-02 18:00 UTC] feat(pipeline): Celery Beat refresh_stale task
  - Added `pipeline.refresh_stale` task to queue scrape for stale institutions (>30 days)
  - Files: `src/pipeline/tasks/pipeline_tasks.py`

- [2026-02-02 18:00 UTC] feat(pipeline): robots.txt compliance check
  - Added `check_robots_txt()` to EnhancedFirecrawlClient
  - Integrated robots check into scrape_overview_page, scrape_funding_pages, scrape_faculty_pages
  - Files: `src/pipeline/clients/firecrawl_enhanced.py`

- [2026-02-02 18:00 UTC] feat(tests): Pipeline unit tests
  - Added tests for FundingExtractor, FacultyExtractor, OverviewExtractor
  - Added tests for EnhancedFirecrawlClient (mocked), DataLakeStorageClient (mocked)
  - Added tests for ProgramExtractor
  - Files: `tests/pipeline/*.py`

- [2026-02-02 18:00 UTC] feat(scorecard): College Scorecard bulk load
  - Added `get_graduate_schools()` generator with pagination and rate limiting
  - Added `load_graduate_schools_from_scorecard()` to DataIngestionService
  - Added Celery task `ingestion.load_scorecard_schools`
  - Added POST `/ingestion/schools/scorecard/load` API endpoint
  - Files: `src/scrapers/schools/scorecard.py`, `src/services/data_ingestion.py`, `src/workers/scraper_worker.py`, `src/routes/data_ingestion.py`

- [2026-02-02 18:00 UTC] feat(pipeline): Program scraping
  - Added ProgramExtractor for graduate program extraction
  - Added `scrape_program_pages()` to EnhancedFirecrawlClient
  - Added `extract_programs_for_institution` Celery task
  - Wired program extraction into run_full_pipeline (overview then programs+funding+faculty)
  - Files: `src/pipeline/extractors/program_extractor.py`, `src/pipeline/clients/firecrawl_enhanced.py`, `src/pipeline/tasks/scrape_tasks.py`, `src/pipeline/tasks/pipeline_tasks.py`

- [2026-02-02 00:00 UTC] feat(pipeline): Scraping pipeline infrastructure
  - Added `ScrapeJob` model for tracking pipeline jobs with status, type, quality metrics
  - Added `FundingOpportunity` model for scholarships, fellowships, assistantships
  - Files: `src/models/scrape_job.py`, `src/models/funding_opportunity.py`

- [2026-02-02 00:00 UTC] feat(pipeline): Pipeline package with schemas, extractors, clients, tasks
  - Created `src/pipeline/` package with full pipeline infrastructure
  - Added Pydantic validation schemas: funding, faculty, school, program
  - Added extractors: FundingExtractor, FacultyExtractor, OverviewExtractor
  - Added EnhancedFirecrawlClient with map_site() and extraction schemas
  - Added DataLakeStorageClient for MinIO/S3 raw data storage
  - Added Celery tasks: scrape_tasks, pipeline_tasks, scheduled_tasks
  - Files: `src/pipeline/**/*`

- [2026-02-02 00:00 UTC] feat(api): Pipeline API endpoints
  - POST `/ingestion/pipeline/run` - trigger full pipeline for institution
  - POST `/ingestion/pipeline/batch` - batch pipeline trigger
  - GET `/ingestion/pipeline/jobs` - list scrape jobs with filtering
  - GET `/ingestion/pipeline/jobs/{job_id}` - get scrape job details
  - Files: `src/routes/data_ingestion.py`

- [2026-02-02 00:00 UTC] feat(infra): Docker services for pipeline
  - Added MinIO service (ports 9000/9001) for data lake storage
  - Added celery-beat service for scheduled task execution
  - Updated celery-worker with multi-queue support (default, scraping, processing)
  - Files: `docker-compose.yml`

- [2026-02-02 00:00 UTC] feat(db): Pipeline database migration
  - Created `scrape_jobs` table with indexes on institution_id, job_type, status
  - Created `funding_opportunities` table with FK to institutions
  - Added columns to institutions: description, acceptance_rate, enrollment_total, grad_enrollment, campus_setting, academic_calendar, last_scraped_at, scrape_status
  - Added columns to programs: duration_months, gre_required, minimum_gpa, last_scraped_at
  - Files: `alembic/versions/012_pipeline_models.py`

### Changed
- [2026-02-02 18:00 UTC] refactor(ingestion): Support scorecard_school_id in upsert
  - Institution upsert now matches on scorecard_school_id when present
  - _apply_seed sets scorecard_school_id
  - Files: `src/services/data_ingestion.py`

- [2026-02-02 00:00 UTC] refactor(celery): Enhanced Celery configuration
  - Added task routing with separate queues for scraping, processing, default
  - Registered pipeline task modules
  - Added Celery Beat schedule for recurring pipeline tasks
  - Files: `src/workers/celery_app.py`, `src/workers/scraper_worker.py`

- [2026-02-02 00:00 UTC] refactor(models): Updated Institution and Program models
  - Institution: added description, acceptance_rate, enrollment_total, grad_enrollment, campus_setting, academic_calendar, last_scraped_at, scrape_status
  - Program: added duration_months, gre_required, minimum_gpa, last_scraped_at
  - Files: `src/models/institution.py`, `src/models/program.py`, `src/models/__init__.py`

- [2026-02-02 00:00 UTC] chore(deps): Added pipeline dependencies
  - Added minio==7.2.9, tenacity==9.0.0
  - Files: `requirements.txt`

- [2026-02-02 00:00 UTC] chore(config): Added pipeline configuration settings
  - MinIO endpoint, credentials, bucket settings
  - Pipeline rate limiting, concurrent domains, off-peak hours
  - Files: `src/config.py`

- [2026-02-02 00:00 UTC] chore(alembic): Registered new models in Alembic env
  - Files: `alembic/env.py`

## [0.0.1] – 2024-01-01

### Added
- Initialized FastAPI project structure
- Configured SQLAlchemy and Alembic for database management
- Created User model with authentication fields
- Set up configuration management with Pydantic Settings
- Created initial health check endpoint
- Set up GitHub Actions CI pipeline for linting and testing
- Added initial Alembic migration for users table

