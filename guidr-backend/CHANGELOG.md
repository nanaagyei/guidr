# CHANGELOG

All notable changes to Guidr Backend will be documented in this file.

## [Unreleased]

### Added
- [2026-03-30 00:20 UTC] chore(ci): Root GitHub Actions CI, pre-commit, and stricter frontend checks
  - Added `.github/workflows/ci.yml` at repo root (backend: Postgres+Redis, ruff, pytest;
    frontend: `next lint --max-warnings 0`, `tsc --noEmit`, `next build`; pre-commit all-files).
  - Added `.pre-commit-config.yaml` (YAML/whitespace, ruff, Next lint + typecheck).
  - Added `pyproject.toml` (ruff + pytest config) and `requirements-dev.txt` (ruff, pytest, pytest-asyncio).
  - Frontend scripts: `typecheck`, `check`; ESLint disables `react-hooks/exhaustive-deps` for stable CI.
  - Files: `/.github/workflows/ci.yml`, `/.pre-commit-config.yaml`, `pyproject.toml`,
    `requirements-dev.txt`, `guidr-frontend/package.json`, `guidr-frontend/.eslintrc.json` (monorepo paths).

- [2026-03-29 UTC] feat(recommendations): AI-powered recommendations via dossier pipeline
  - Rewired `POST /recommendations/request` to use DossierService + Celery async pipeline
  - Creates RecommendationSession upfront (status=pending), dispatches to dossier graph
  - `_promote_recommendations()` now writes RecommendationResult rows from AI JSON output
  - Added session_id pass-through: route → DossierService → Celery task → graph state
  - Files: `src/routes/recommendations.py`, `src/services/dossier_service.py`,
    `src/pipeline/tasks/dossier_tasks.py`, `src/pipeline/orchestrator/dossier_state.py`,
    `src/pipeline/orchestrator/dossier_nodes.py`

- [2026-03-29 UTC] feat(recommendations): Save school flow with deep research triggers
  - `POST /recommendations/results/{id}/save` — saves rec, materializes Institution/Program,
    triggers school_dossier + professor_match + funding_dossier pipelines
  - `GET /recommendations/saved` — lists saved recs with pipeline job statuses
  - `DELETE /recommendations/saved/{id}` — removes saved recommendation
  - Files: `src/routes/recommendations.py`, `src/models/saved_recommendation.py`

- [2026-03-29 UTC] feat(schema): Migration 018 — AI recommendation columns + saved_recommendations
  - Converts PG enums (tier, status) to VARCHAR(20) for ORM compatibility
  - Makes program_id nullable on recommendation_results (AI recs have no DB program yet)
  - Adds AI metadata columns: school_name, program_name, institution_city/country,
    funding_summary, deadline, website_url
  - Creates saved_recommendations table with FK refs to pipeline_jobs
  - Files: `alembic/versions/018_recommendation_ai_columns.py`,
    `src/models/recommendation_result.py`, `src/models/saved_recommendation.py`,
    `src/models/__init__.py`

- [2026-03-29 UTC] feat(frontend): Save school button + saved schools dashboard tile
  - Added `saveRecommendation()`, `getSavedRecommendations()`, `unsaveRecommendation()` API functions
  - RecommendationCard: Save School button, funding_summary, deadline, website_url display
  - SavedSchoolsTile: shows saved recommendations with research progress indicators
  - Updated generating message to "Researching programs... 30-60 seconds"
  - Files: `guidr-frontend/src/utils/api.ts`, `guidr-frontend/src/components/RecommendationCard.tsx`,
    `guidr-frontend/src/app/recommendations/page.tsx`,
    `guidr-frontend/src/components/dashboard/SavedSchoolsTile.tsx`

### Changed
- [2026-03-29 UTC] refactor(stub): Updated PerplexityStubProvider recommendation output
  - Returns 5 realistic recommendations matching prompt schema (school_name, program_name,
    tier, score, explanation, funding_summary, deadline, website_url)
  - Added tier_counts and methodology for schema compliance
  - Files: `src/pipeline/research_gateway/providers/perplexity_stub.py`

- [2026-03-29 UTC] refactor(recommendations): Dual-path result rendering for GET /latest and /session
  - `_build_result_dict()` helper reads AI metadata from result columns when program_id is null,
    falls back to Program/Institution join for legacy results
  - Includes result_id, is_saved, saved_id in response for frontend save flow
  - Files: `src/routes/recommendations.py`

### Fixed
- [2026-03-29 UTC] fix(recommendations): Stop 404 spam from GET /recommendations/latest
  - Return empty result `{session_id: null, results: []}` instead of 404 when no completed sessions
  - Frontend normalizes empty response to `null` for backward compat
  - Files: `src/routes/recommendations.py`, `guidr-frontend/src/utils/api.ts`

- [2026-03-29 UTC] fix(recommendations): Surface errors from POST /recommendations/request
  - Remove silent `except: pass` — now marks session as `failed` with `error_message`
  - Refresh ORM session after `generate_recommendations()` so response returns actual status
  - Frontend handles immediate failure/completion instead of always polling
  - Files: `src/routes/recommendations.py`, `guidr-frontend/src/app/recommendations/page.tsx`

### Added
- [2026-03-28 UTC] feat(pipeline): Wire document upload → parse → extract pipeline end-to-end
  - Connected `POST /documents/{id}/confirm` to Celery task `document.process` (was TODO)
  - Registered `src.workers.document_processor` in Celery include list
  - Wrapped `process_document` as `@shared_task` with retry (max 3, 30s delay)
  - After transcript extraction, auto-recalculate `profile_completion_score`
  - Files: `src/workers/document_processor.py`, `src/workers/celery_app.py`, `src/routes/documents.py`

- [2026-03-28 UTC] feat(academic-records): Add PUT endpoint for updating records
  - New `PUT /academic-records/{id}` endpoint with partial update support
  - `AcademicRecordUpdate` schema (all fields optional)
  - Recalculates normalized GPA and profile completion on update
  - Files: `src/routes/academic_records.py`, `src/schemas/academic_record.py`

- [2026-03-28 UTC] feat(academic-records): Return completion data in POST/PUT responses
  - Embed full `completion` object (percent, level, missing_fields, unlocks) in response
  - Avoids extra round-trip to `/profile/completion` after record changes
  - Files: `src/routes/academic_records.py`, `src/schemas/academic_record.py`

- [2026-03-28 UTC] feat(frontend): Fix profile completion refresh after academic record CRUD
  - Call `refreshCompletion()` after create, update, delete, and transcript upload
  - Replace 5s setTimeout with proper 3s polling (max 60s) for transcript processing
  - Toast notification on profile level-up
  - Files: `src/app/academic-records/page.tsx`

- [2026-03-28 UTC] feat(frontend): Fix broken dashboard navigation links
  - CalendarTile "View All" → `/schools` (was `/dashboard/calendar` 404)
  - AppliedSchoolsTile "Manage Applications" → `/recommendations` (was `/dashboard/applications` 404)
  - Created `/help/getting-started` page with onboarding steps
  - Created `/help/faq` page with accordion FAQ
  - Files: `CalendarTile.tsx`, `AppliedSchoolsTile.tsx`, `src/app/help/getting-started/page.tsx`, `src/app/help/faq/page.tsx`

- [2026-03-28 UTC] feat(frontend): Wire RecommendationExplainModal to recommendation cards
  - Added `onExplain` prop to `RecommendationCard` with "Why This?" button
  - Connected to existing `setExplainRec` state in recommendations page
  - Files: `src/components/RecommendationCard.tsx`, `src/app/recommendations/page.tsx`

- [2026-03-28 UTC] feat(frontend): ProfileHealthBanner component for feature-gated pages
  - Reusable banner showing missing fields + CTA when profile level insufficient
  - Added to Funding and Professors pages
  - Files: `src/components/ProfileHealthBanner.tsx`, `src/app/funding/page.tsx`, `src/app/professors/page.tsx`

- [2026-03-28 UTC] feat(frontend): Sidebar profile completion indicator
  - Progress bar with level/percentage when sidebar expanded
  - Compact ring when sidebar collapsed
  - Hidden at Level 3 (fully complete)
  - Files: `src/components/Sidebar.tsx`

- [2026-03-28 UTC] feat(frontend): Academic records cross-link on profile page
  - Card showing record count with CTA to add records when missing
  - Files: `src/app/profile/page.tsx`

- [2026-03-28 UTC] feat(frontend): Academic record edit support
  - Edit button on each record card, pre-populated form modal
  - Calls `PUT /academic-records/{id}` via `putAcademicRecord` API function
  - Files: `src/app/academic-records/page.tsx`, `src/utils/api.ts`

### Added (previous)
- [2026-03-28 UTC] feat(ux): Major UX overhaul — onboarding, profile completion, sidebar, input parsing
  - **Onboarding wizard rewrite**: visual stepper, localStorage draft persistence, per-step validation,
    live profile preview panel (desktop), "Finish later" option, direction-aware spring transitions,
    "Why we ask this" tooltips
  - **Profile completion levels**: 3-tier level system (Basics → Targeting → Full) replacing flat percentage,
    `GET /profile/completion` endpoint, `ProfileCompletionResponse` schema, `require_level()` FastAPI dependency
  - **Feature gating**: server-side 403 with actionable missing_fields on locked features (recommendations, funding, professors),
    sidebar lock icons + redirect to onboarding, updated OnboardingGuard to use level-based checks
  - **Sidebar pin/collapse**: explicit `mode`+`pinned` state with localStorage persistence, Pin icon when collapsed,
    X icon when pinned, smooth AnimatePresence transitions
  - **Input parsing**: TagInput paste handler (comma-split), `maxTagLength` prop, backend Pydantic `normalize_list_fields`
    validator, shared `sanitization.py` utility (normalize_string_list, sanitize_text, SAFE_TEXT_PATTERN)
  - **Dashboard**: enhanced ProfileCompletionTile with levels + missing fields checklist, ResearchJobsTile
  - **Recommendations**: RecommendationExplainModal, regeneration confirmation dialog, idempotency keys (Redis, 1hr TTL)
  - **ProfileCompletionContext**: React context for global completion state with refresh callback
  - New files:
    - Backend: `src/utils/sanitization.py`, `src/dependencies/feature_gate.py`
    - Frontend: `src/components/onboarding/validation.ts`, `src/hooks/useOnboardingDraft.ts`,
      `src/components/onboarding/OnboardingStepper.tsx`, `src/components/onboarding/ProfilePreview.tsx`,
      `src/contexts/ProfileCompletionContext.tsx`, `src/components/RecommendationExplainModal.tsx`,
      `src/components/dashboard/ResearchJobsTile.tsx`
  - Modified files:
    - Backend: `src/utils/profile_completion.py`, `src/routes/profile.py`, `src/schemas/profile.py`,
      `src/schemas/dossier_schemas.py`, `src/routes/recommendations.py`, `src/routes/professors.py`,
      `src/routes/funding.py`
    - Frontend: `src/components/OnboardingWizard.tsx`, `src/components/OnboardingGuard.tsx`,
      `src/components/Sidebar.tsx`, `src/components/ui/sidebar.tsx`, `src/components/ui/tag-input.tsx`,
      `src/components/dashboard/ProfileCompletionTile.tsx`, `src/app/layout.tsx`,
      `src/app/dashboard/page.tsx`, `src/app/recommendations/page.tsx`, `src/utils/api.ts`

- [2026-03-26 UTC] feat(pipeline): Agentic research pivot — RFC open questions resolved
  - Confidence thresholds lowered to promote ≥0.78, stage 0.55–0.77, warn <0.55; auto-repair removed (on-demand only)
  - Broader source trust scoring: official=1.0, aggregators=0.8, .edu/.gov=0.7, reputable=0.5, other=0.3
  - Per-user enrichment_cache entries (user_id FK) with per-user→global fallback in DossierService
  - External funding opportunities (NSF, NIH, NDSEG, etc.) added to funding dossier schema and prompts
  - Files: `src/pipeline/processors/confidence_scorer.py`, `src/services/dossier_service.py`, `src/models/enrichment_cache.py`, `src/pipeline/schemas/funding_schemas.py`, `src/pipeline/prompts/templates/funding_dossier_v1.txt`, `src/pipeline/prompts/templates/funding_dossier_repair_v1.txt`

- [2026-03-26 UTC] feat(profile): Add research_areas and career_goals to UserProfile
  - New JSONB `research_areas` and TEXT `career_goals` columns in `user_profiles`
  - Schema, migration (017), and dossier/professor context builders updated to use these fields
  - Files: `src/models/user_profile.py`, `src/schemas/profile.py`, `alembic/versions/017_user_profile_research_areas.py`, `src/pipeline/orchestrator/dossier_nodes.py`, `src/pipeline/orchestrator/professor_nodes.py`

- [2026-03-26 UTC] feat(api): Add dashboard data endpoints
  - `GET /schools/saved` — user's researched/recommended schools
  - `GET /dossiers/professors/recommended` — aggregated professor matches across saved schools
  - `GET /dossiers/deadlines` — upcoming application deadlines from school dossiers
  - Files: `src/routes/schools.py`, `src/routes/dossiers.py`

- [2026-03-26 UTC] feat(frontend): TagInput chip component + onboarding wire-up
  - New `TagInput` component: chip tags on comma/Enter, spaces preserved within tags, backspace removes last tag
  - OnboardingWizard: `preferred_countries`, `preferred_cities`, `research_areas`, `secondary_fields` now use TagInput
  - ApplicationSettings: research_areas TagInput + career_goals textarea wired to `putProfile()`
  - Files: `guidr-frontend/src/components/ui/tag-input.tsx`, `guidr-frontend/src/components/OnboardingWizard.tsx`, `guidr-frontend/src/components/settings/ApplicationSettings.tsx`

- [2026-03-26 UTC] feat(frontend): Dynamic dashboard tiles with real API data
  - ProfessorsTile, SavedSchoolsTile, CalendarTile, AppliedSchoolsTile replaced mock data with live API calls
  - Each tile fetches independently with skeleton loaders (no full-page blocking)
  - CalendarTile: urgency computed client-side from deadline date; shows "unverified" warning for low-confidence data
  - New API helpers: `getSavedSchools`, `getRecommendedProfessors`, `getUpcomingDeadlines`
  - Files: `guidr-frontend/src/components/dashboard/*.tsx`, `guidr-frontend/src/utils/api.ts`

- [2026-03-27 UTC] feat(ingestion): Return Celery task_id for async scorecard load
  - `POST /ingestion/schools/scorecard/load` with `async_run: true` now includes `task_id` and `task` name for progress checks
  - Files: `src/routes/data_ingestion.py`

### Security
- [2026-03-26 UTC] feat(auth): Add internal API key auth for pipeline and ingestion endpoints
  - New `INTERNAL_API_KEY` config setting in `src/config.py`
  - New `require_internal_api_key` and `require_admin_or_internal_key` dependencies
  - Pipeline admin and ingestion routes now accept `X-Internal-Key` header alongside admin session
  - Files: `src/config.py`, `src/dependencies/auth.py`, `src/routes/pipeline.py`, `src/routes/data_ingestion.py`, `.env.example`

### Changed
- [2026-03-26 23:00 UTC] docs(pipeline): Overhaul all pipeline and enrichment documentation
  - Rewrote all 6 docs to use `X-Internal-Key` header for admin/ingestion auth (replaces `Authorization: Bearer`)
  - Streamlined Quick Start to a linear 10-minute setup flow
  - Consolidated Pipeline Guide into single architecture + components + API reference
  - Reduced Enrichment Verification from 1046 to 348 lines while keeping all verification steps
  - Updated Integration Summary with auth table and recommended 3-phase workflow
  - Simplified Comprehensive Data Collection to focus on 4 collection methods with scale guidance
  - Updated R2 Setup with current env vars and cookie-based auth
  - Files: `docs/QUICK_START.md`, `docs/PIPELINE_GUIDE.md`, `docs/ENRICHMENT_PIPELINE_VERIFICATION.md`, `docs/INTEGRATION_SUMMARY.md`, `docs/COMPREHENSIVE_DATA_COLLECTION_GUIDE.md`, `docs/R2_SETUP.md`

- [2026-03-26 UTC] refactor(auth): Remove email 2FA requirement from login flow
  - Login now uses email + password only (no verification code)
  - Email code verification remains required for registration and password reset
  - `POST /auth/2fa/send` rejects `purpose="login"` to prevent sending login codes
  - `UserLogin` schema no longer includes `verification_code` field
  - Frontend login page simplified to single-step email/password submit
  - Files: `src/routes/auth.py`, `src/routes/two_factor.py`, `src/schemas/auth.py`, `guidr-frontend/src/app/auth/login/page.tsx`, `guidr-frontend/src/utils/api.ts`

- [2026-03-26 UTC] feat(auth): Implement true 30-day remember-me persistence
  - JWT `exp` and cookie `max_age` both align to 30 days when `remember_me=True`
  - Default (non-remember) login uses 24-hour token with session-scoped cookie
  - `create_access_token` now accepts optional `expires_delta` parameter
  - Files: `src/utils/jwt.py`, `src/routes/auth.py`

### Fixed
- [2026-03-27 UTC] fix(routes): Close try/except in dossiers deadlines endpoint
  - `get_upcoming_deadlines` had an unclosed `try` block causing `SyntaxError` on import
  - Files: `src/routes/dossiers.py`

- [2026-03-27 UTC] fix(config): Accept OPEN_ALEX_* env names for OpenAlex settings
  - `OPEN_ALEX_API_KEY` / `OPEN_ALEX_RPS` were rejected as extra fields; they now map to `openalex_api_key` / `openalex_rps` via `AliasChoices` alongside `OPENALEX_*`
  - Documented academic API vars in `.env.example`
  - Files: `src/config.py`, `.env.example`

- [2026-03-27 UTC] fix(api): Handle duplicate enrichment fingerprint races without 500
  - `POST /pipeline/enrich` now catches `IntegrityError` from unique `pipeline_jobs.fingerprint` collisions
  - Returns `dedup_in_progress` (with existing job when available) instead of raising 500
  - Files: `src/services/enrichment_service.py`

- [2026-03-27 UTC] fix(pipeline): Pass LangGraph configurable thread_id in Celery graph invocations
  - Fixed `ValueError: Checkpointer requires one or more of ... thread_id, checkpoint_ns, checkpoint_id` during enrichment runs
  - Added `config={"configurable": {"thread_id": ...}}` to `graph.invoke(...)` in orchestrator, dossier, professor-match, and direct orchestrator tasks
  - Files: `src/pipeline/tasks/orchestrator_tasks.py`, `src/pipeline/tasks/dossier_tasks.py`, `src/pipeline/tasks/pipeline_tasks.py`

- [2026-03-26 UTC] fix(ingestion): Repair bulk-enrich fingerprint dedup calling wrong API
  - `bulk_enrich` passed invalid `category=` to `compute_job_fingerprint` and called `find_recent_success` with unsupported `fingerprint=` kwarg
  - Now uses `JobRepository.find_in_progress` / `find_recent_success` with the same fingerprint inputs as `create_job` (`target_url`, `freshness_bucket="default"`)
  - Commits after each queued job so mid-batch duplicate fingerprints do not roll back prior rows; catches `IntegrityError` for race duplicates
  - Files: `src/routes/data_ingestion.py`

- [2026-03-26 UTC] fix(db): Auto-apply Alembic migrations on server startup
  - `run.py` now calls `alembic upgrade head` before starting uvicorn
  - Prevents `relation "users" does not exist` errors on fresh databases
  - Files: `run.py`

- [2026-03-26 UTC] fix(auth): Handle `ProgrammingError` in check-email endpoint
  - Missing tables now return 503 instead of unhandled 500
  - Files: `src/routes/auth.py`

- [2026-03-26 UTC] fix(email): Improve SMTP error reporting in 2FA email service
  - Separate error handling for authentication, connection, and general failures
  - Clearer log messages for SMTP credential and connection issues
  - Files: `src/services/email.py`

### Changed
- [2025-03-23 UTC] chore(deps): Update requirements.txt for Python 3.10+ and latest compatible versions
  - Added Python 3.10+ requirement (langchain, langgraph require 3.10+; pip fails on 3.9)
  - Replaced strict pins (==) with ranged constraints (>=,<) for patch/minor updates
  - Widened langgraph to >=1.0.8,<2.0.0 (allows 1.1.x)
  - Files: `requirements.txt`

### Added
- [2026-03-04 UTC] test(pipeline): Add 9 legacy pipeline test files (106+ tests)
  - `test_confidence_scorer.py`: 17 tests — pure function tests for scoring source, extraction, validation, staleness, and promote/repair boundaries
  - `test_job_repository.py`: 12 tests — create_job fingerprinting, find_recent_success, find_in_progress, claim_job, complete_job, cancel_job, requeue_job
  - `test_enrichment_service.py`: 8 tests — cache hit, force refresh, quota exceeded, dedup, dispatch routing for dossier/professor_match
  - `test_research_gateway.py`: 8 tests — cache hit/miss, result caching, FAILED not cached, dossier response, dedupe key determinism, source document persistence, stub selection
  - `test_redis_primitives.py`: 20 tests — key format, fingerprint determinism, URL hash normalization, lock acquire/release, quota allowed/exceeded/fail-open, rate limit take_token, host extraction, circuit breaker trip/reset
  - `test_domain_health.py`: 10 tests — record_success/error, block at threshold, is_blocked (Redis, Postgres, cooldown), get_all_health, reset_stale_blocks
  - `test_orchestrator_nodes.py`: 15 tests — load_context, discover_urls, canonicalize_urls, fetch_page, extract_structured, score_confidence
  - `test_pipeline_api.py`: 12 tests — /pipeline/enrich, /pipeline/enrich/shortlist, /pipeline/cache/*, /pipeline/jobs/*, admin endpoints
  - `test_maintenance_tasks.py`: 6 tests — purge_expired_cache, reset_domain_health, cleanup_old_jobs
  - `conftest.py`: Test infrastructure mocking src.db, pgvector, and celery for test environment without psycopg2
  - Files: `tests/pipeline/test_confidence_scorer.py`, `tests/pipeline/test_job_repository.py`, `tests/pipeline/test_enrichment_service.py`, `tests/pipeline/test_research_gateway.py`, `tests/pipeline/test_redis_primitives.py`, `tests/pipeline/test_domain_health.py`, `tests/pipeline/test_orchestrator_nodes.py`, `tests/pipeline/test_pipeline_api.py`, `tests/pipeline/test_maintenance_tasks.py`, `tests/pipeline/conftest.py`

### Fixed
- [2026-03-04 UTC] fix(deps): Upgrade sentence-transformers for Python 3.13 compatibility
  - sentence-transformers 3.0.1 pulled tokenizers 0.19.x which requires Rust to compile on Python 3.13 (no pre-built wheels)
  - Upgraded to sentence-transformers>=5.2.0,<6.0.0 which uses tokenizers 0.22+ with pre-built wheels for Python 3.13
  - Files: `requirements.txt`

- [2026-03-04 UTC] fix(pipeline): Fix 6 bugs in dossier system
  - **Dedup fingerprint mismatch (HIGH)**: `DossierService.find_in_progress()` now passes `freshness_bucket` to match `create_job()`, preventing duplicate jobs
  - **GPA always N/A (HIGH)**: `load_dossier_context` now queries `AcademicRecord` for GPA instead of non-existent `profile.gpa`
  - **No dossier stub provider (MEDIUM)**: Added `extract_dossier()` to `PerplexityStubProvider` with category-specific synthetic data for dev/test
  - **Dead graph decision (LOW)**: Removed unused `post_fallback_decision` function, replaced conditional edge with direct edge in dossier graph
  - **Dead imports in DossierService (LOW)**: Removed unused `acquire_lock`, `release_lock`, `compute_job_fingerprint` imports
  - **Dead imports in dossiers route (LOW)**: Removed unused `DossierCacheValue` and `DossierResponseSchema` imports
  - Files: `src/services/dossier_service.py`, `src/pipeline/orchestrator/dossier_nodes.py`, `src/pipeline/research_gateway/providers/perplexity_stub.py`, `src/pipeline/orchestrator/dossier_graph.py`, `src/routes/dossiers.py`
  - Also fixed pre-existing test bug in `test_dossier_nodes.py` (incorrect side_effect ordering for user profile query)

- [2026-03-04 UTC] test(pipeline): Add unit tests for orchestrator nodes, pipeline API, and maintenance tasks
  - `test_orchestrator_nodes.py`: 15 tests covering load_context, discover_urls, canonicalize_urls, fetch_page, extract_structured, score_confidence with mocked DB and services
  - `test_pipeline_api.py`: 12 tests covering /pipeline/enrich, /pipeline/enrich/shortlist, /pipeline/cache/*, /pipeline/jobs/*, and admin endpoints via TestClient
  - `test_maintenance_tasks.py`: 6 tests covering purge_expired_cache, reset_domain_health, cleanup_old_jobs with mocked SessionLocal
  - Files: `tests/pipeline/test_orchestrator_nodes.py`, `tests/pipeline/test_pipeline_api.py`, `tests/pipeline/test_maintenance_tasks.py`

- [2026-03-04 UTC] docs: Update documentation for agentic dossier system
  - Updated `docs/IMPLEMENTATION_STATUS.md` with Skill 29 section (all 9 phases, 39 tests)
  - Updated `docs/QUICK_START.md` with dossier endpoints and new env vars (PERPLEXITY, S2, OpenAlex)
  - Updated `docs/PIPELINE_GUIDE.md` with DossierGraph, ProfessorMatchGraph, academic clients, dossier API endpoints, migration 016 schema
  - Updated `docs/ENRICHMENT_PIPELINE_VERIFICATION.md` with dossier verification steps (migration check, graph test, API tests, citation verification, test commands)
  - Files: `docs/IMPLEMENTATION_STATUS.md`, `docs/QUICK_START.md`, `docs/PIPELINE_GUIDE.md`, `docs/ENRICHMENT_PIPELINE_VERIFICATION.md`

- [2026-03-04 UTC] feat(pipeline): Agentic enrichment migration — dossier system
  - Migration 016: `evidence_map_json` on extraction_runs, `openalex_id`/`semantic_scholar_id`/`orcid_id` (indexed) on professors, `citations_json`/`evidence_map_json` on enrichment_cache, `pipeline_job_id` FK + `citations_json` on recommendation_sessions, `citations_json`/`evidence_map_json` on recommendation_results
  - Config: `enable_agentic_dossiers`, `enable_scrape_fallback`, `enable_bulk_scrape` feature flags; `semantic_scholar_api_key`, `openalex_api_key`, `semantic_scholar_rps`, `openalex_rps` settings
  - Research Gateway: `DossierCitation`, `DossierResponse` schemas; `extract_dossier()` abstract method on `BaseResearchProvider`; Perplexity `extract_dossier()` implementation with citation parsing and evidence_map building; category-specific TTLs in gateway service
  - Academic API clients: `SemanticScholarClient` (search_author, get_author, get_author_papers) with Redis rate limiting at 1 rps; `OpenAlexClient` (search_authors, get_author, get_institution, search_works) with Redis rate limiting at 10 rps
  - Prompt templates: `recommendation_run_v1.txt` (30 schools in 4 tiers), `school_dossier_v1.txt` (overview/URLs/requirements/funding), `professor_synthesis_v1.txt` (rank candidates from API data), `funding_dossier_v1.txt` (fellowships/TA/RA/scholarships), plus 3 repair templates; all include injection guard
  - DossierGraph (LangGraph): load_dossier_context → research_extract → validate_citations → score_dossier_confidence → stage_dossier → promote_dossier, with fallback_scrape conditional on confidence < 0.70
  - ProfessorMatchGraph (LangGraph): load_professor_context → query_openalex → enrich_semantic_scholar → synthesize_rank → stage_professor_matches → promote_professor_matches
  - Celery tasks: `pipeline.run_dossier`, `pipeline.run_professor_match` with same claim/lock/invoke/complete pattern
  - DossierService: cache → quota → dedup → dispatch for school_dossier, funding_dossier, professor_match, recommendation_run; freshness buckets with category encoding
  - EnrichmentService: new dossier freshness buckets, dispatch routing for dossier/professor_match job types
  - API routes: `POST /dossiers/schools/{id}/research`, `POST /dossiers/schools/{id}/professors/match`, `POST /dossiers/schools/{id}/funding/research`, `POST /recommendations/run`
  - Pydantic schemas: `DossierRequest`, `DossierResponseSchema`, `DossierCacheValue`, `ProfessorMatchRequest`, `FundingDossierRequest`, `RecommendationRunRequest`
  - Tests: unit tests for dossier nodes, professor nodes, academic clients, dossier service; integration tests for DossierGraph and ProfessorMatchGraph; API route tests
  - Files: `alembic/versions/016_dossier_system.py`, `src/config.py`, `src/models/extraction_run.py`, `src/models/professor.py`, `src/models/enrichment_cache.py`, `src/models/recommendation_session.py`, `src/models/recommendation_result.py`, `src/pipeline/research_gateway/schemas.py`, `src/pipeline/research_gateway/providers/base.py`, `src/pipeline/research_gateway/providers/perplexity.py`, `src/pipeline/research_gateway/service.py`, `src/pipeline/clients/semantic_scholar.py`, `src/pipeline/clients/openalex.py`, `src/pipeline/prompts/templates/recommendation_run_v1.txt`, `src/pipeline/prompts/templates/school_dossier_v1.txt`, `src/pipeline/prompts/templates/professor_synthesis_v1.txt`, `src/pipeline/prompts/templates/funding_dossier_v1.txt`, `src/pipeline/prompts/templates/recommendation_repair_v1.txt`, `src/pipeline/prompts/templates/school_dossier_repair_v1.txt`, `src/pipeline/prompts/templates/funding_dossier_repair_v1.txt`, `src/pipeline/orchestrator/dossier_state.py`, `src/pipeline/orchestrator/dossier_nodes.py`, `src/pipeline/orchestrator/dossier_graph.py`, `src/pipeline/orchestrator/professor_state.py`, `src/pipeline/orchestrator/professor_nodes.py`, `src/pipeline/orchestrator/professor_graph.py`, `src/pipeline/tasks/dossier_tasks.py`, `src/services/dossier_service.py`, `src/services/enrichment_service.py`, `src/routes/dossiers.py`, `src/routes/recommendations.py`, `src/schemas/dossier_schemas.py`, `src/main.py`, `src/workers/celery_app.py`

- [2026-02-20 UTC] feat(pipeline): Enrichment tracking columns + domain health wire-up + bulk rescrape
  - Migration 015: added `last_enriched_at`, `last_enrichment_confidence`, `data_version` to institutions, programs, professors, funding_opportunities (with indexes on institutions/programs)
  - `promote_write` node now sets all three enrichment columns after successful promotion, including FundingOpportunity support
  - `fetch_page` node now fully wires DomainHealthService: `is_blocked()` check before fetch, `record_success()` / `record_error()` after
  - Prompt templates: `synthesis_v1.txt` (120-word UI-safe summary) and `fill_missing_v1.txt` (repair partial extraction)
  - `POST /ingestion/pipeline/bulk-enrich` endpoint: queues LangGraph enrichment jobs for all entities of a given kind with freshness dedup and fingerprint skipping
  - `scripts/reset_data.py`: full data reset script (pipeline tables + canonical entities) with --dry-run and --yes flags
  - `InstitutionResponse` schema: added `last_enriched_at`, `last_enrichment_confidence`, `data_version` fields
  - `GET /programs` response: added `data_completeness_score` and `last_enriched_at` to each program result
  - Files: `alembic/versions/015_add_enrichment_tracking_columns.py`, `src/models/institution.py`, `src/models/program.py`, `src/models/professor.py`, `src/models/funding_opportunity.py`, `src/pipeline/orchestrator/nodes.py`, `src/pipeline/prompts/templates/synthesis_v1.txt`, `src/pipeline/prompts/templates/fill_missing_v1.txt`, `scripts/reset_data.py`, `src/routes/data_ingestion.py`, `src/routes/programs.py`, `src/schemas/institution.py`

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

