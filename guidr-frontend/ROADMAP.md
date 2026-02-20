# Guidr Roadmap

This document outlines the development milestones for Guidr MVP.

> Last updated: 2026-02-20

---

## Milestone 0: Project Bootstrapping & Foundations
**Status:** ✅ Complete

Set up both backend and frontend repositories with basic infrastructure, CI pipelines, and documentation.

**Delivered:**
- Next.js 14 (App Router) + TypeScript frontend with shadcn/ui design system
- FastAPI + PostgreSQL + Redis + Celery + Meilisearch backend
- Docker Compose services (postgres, redis, meilisearch, minio, celery-worker, celery-beat)
- Alembic migrations (001–015), GitHub Actions CI

---

## Milestone 1: Authentication & App Shell
**Status:** ✅ Complete

Implement user registration, login, JWT authentication, and basic dashboard shell.

**Delivered:**
- Email/password registration and login with JWT access tokens
- Two-factor authentication (TOTP codes via email)
- Password reset flow (email link)
- "Keep me signed in" (30-day session cookie)
- Sidebar navigation shell with all main routes
- Dashboard with 7 tiles (Recommended Programs, Profile Completion, Essays, Recommendations, Professors, Documents, Settings)

---

## Milestone 2: User Profile & Academic Data
**Status:** ✅ Complete

Enable users to create and edit profiles, add academic records, and track profile completion.

**Delivered:**
- Profile page: name, email, bio, target degree, fields of interest
- Academic records: GPA, GRE/GMAT/TOEFL scores, undergraduate institution
- Profile completion score displayed in dashboard tile
- Onboarding wizard (multi-step profile setup)
- Privacy settings

---

## Milestone 3: School & Program Search
**Status:** 🔄 In Progress

Build program search functionality with filters, program detail pages, and manual data seeding.

**Delivered:**
- Institutions page with search, country/type/control filters, modal detail view
- Programs (Schools) page with degree, field, country, and tuition filters
- Program detail pages (`/programs/[id]`)
- Meilisearch integration for full-text search with DB fallback
- College Scorecard bulk load endpoint (`POST /ingestion/schools/scorecard/load`)
- Enrichment freshness badge on InstitutionCard and ProgramCard (`last_enriched_at`)

**Remaining:**
- Populate database at scale (run reset → scorecard load → bulk-enrich pipeline)
- Program detail pages need richer enriched content (description, requirements, deadlines)
- Add institution detail page (`/institutions/[id]`)

---

## Milestone 4: Document Upload & Extraction
**Status:** 🔄 In Progress

Implement document upload to R2, OCR processing, and LLM-powered extraction for transcripts and resumes.

**Delivered:**
- Document upload routes and DB model
- Document list page in frontend
- Storage abstraction (MinIO local / S3 production)

**Remaining:**
- OCR pipeline (Tesseract / AWS Textract) for transcript PDFs
- LLM extraction of GPA, courses, dates from uploaded transcripts
- Auto-populate academic records from uploaded transcript
- Resume parsing to pre-fill profile fields

---

## Milestone 5: Essay Management & Review
**Status:** 🔄 In Progress

Create essay management system with versioning and LLM-powered structured feedback.

**Delivered:**
- Essay model with versioning (`EssayVersion`) and review (`EssayReview`)
- Essays page in frontend
- Essays route with CRUD operations

**Remaining:**
- LLM-powered structured feedback (clarity, argument strength, grammar)
- Essay prompt suggestions based on target program
- Side-by-side version comparison UI

---

## Milestone 6: Recommendations Engine
**Status:** 🔄 In Progress

Build heuristic recommendation system that scores programs and assigns tiers (Dream/Reach/Target/Safety).

**Delivered:**
- `RecommendationEngine` utility with GPA/GRE/field matching heuristics
- `POST /recommendations` endpoint
- Tier assignment (Dream / Reach / Target / Safety) based on score gap
- RecommendedSchoolsTile in dashboard

**Remaining:**
- Integrate enriched program data (acceptance rate, GPA cutoffs) into scoring
- Weight research fit (professor interest overlap with user interests)
- Shortlist management (save/unsave programs)
- Notification when a saved program deadline is approaching

---

## Milestone 7: Professor Finder & Cold Email Drafts
**Status:** 🔄 In Progress

Implement professor search and LLM-generated personalized email drafts.

**Delivered:**
- Professors DB model and search route (`GET /professors`)
- Professors page in frontend with name/institution/interest search
- `OutreachEmail` model for storing drafts
- `email_generator.py` service stub

**Remaining:**
- LLM cold-email generation using professor research interests + user profile
- Send/track outreach emails from the UI
- Professor enrichment via LangGraph pipeline (scrape faculty pages)
- Is-accepting-students heuristic from faculty page content

---

## Milestone 8: Polish, QA & Private Beta
**Status:** 🔄 Pending

Polish UI/UX, optimize performance, conduct QA testing, and launch private beta.

**To Do:**
- End-to-end QA across all user flows
- Lighthouse performance audit and optimization
- Mobile responsiveness pass
- Error boundary coverage and 404/500 pages
- Rate limit tuning and load testing
- Private beta invite system (waitlist → invite codes)
- Analytics integration (Posthog / Plausible)

---

## Milestone 9: Data Pipeline & Enrichment at Scale *(Added 2026-02-20)*
**Status:** 🔄 In Progress

Populate the database with real school, program, professor, and funding data using the LangGraph enrichment pipeline.

**Delivered (Infrastructure):**
- LangGraph 15-node orchestrator (discover → fetch → extract → validate → score → promote)
- Research Gateway with Perplexity Sonar provider + stub fallback
- Firecrawl integration for web page fetching
- LLM extractors for overview, programs, faculty, funding
- ConfidenceScorer (0.35×source + 0.35×extraction + 0.25×validation + 0.05×staleness)
- Domain health tracking (auto-block misbehaving domains, Redis + Postgres)
- Pipeline job deduplication via SHA256 fingerprint
- Per-domain token-bucket rate limiting (Lua scripts)
- Per-user quota enforcement (50 enrichments/day)
- Enrichment cache with staleness windows (7d deadlines, 14d programs, 30d overview)
- Maintenance tasks: purge cache, reset domain blocks, cleanup old jobs (Celery Beat)
- `POST /ingestion/pipeline/bulk-enrich` — queues enrichment for all entities of a kind
- `scripts/reset_data.py` — full data wipe with --dry-run

**Remaining:**
- **Run the pipeline** — seed from College Scorecard then trigger bulk-enrich
- Write pipeline test suite (10 test files — all missing)
- Add `OpenDeepResearchAdapter` (alternative to Perplexity)
- Add per-endpoint HTTP rate limiting middleware
- Add `validation_reports` and `confidence_scores` dedicated tables
- Tune Celery worker concurrency per worker type (research/fetch/extract/validate)

---

## Future Enhancements (Post-MVP)

- Full application tracking system
- Advanced notification system
- Credit-based payment system
- Extended AI chat assistant (advisor bot)
- Large-scale data scraping (international universities)
- Mobile app (React Native)
- Multi-language support
- User community features
- Prompt A/B testing for extraction quality improvement
- OpenDeepResearch integration for richer synthesis
