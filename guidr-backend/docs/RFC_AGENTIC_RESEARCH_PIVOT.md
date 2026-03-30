RFC: Agentic Research Pivot for Guidr Backend

Status: Adopted + Implemented (2026-03-26)
Owner: Guidr Backend
Last updated: 2026-03-26
Audience: Backend, Frontend, Product, Security/Infra

⸻

1) Summary

Guidr currently relies on scraping (e.g., Firecrawl) as a primary mechanism to collect school/program/professor/funding data. This approach is now blocked by token limits and has inherent long-term drawbacks: brittle parsing, inconsistent site structures, higher legal/ToS risk, and escalating maintenance.

This RFC proposes a pivot to an agent-first, research-driven backend that uses deep research tools (Perplexity Deep Research and optionally LangChain/LangGraph Open Deep Research) to generate structured, citation-backed artifacts (recommendations, school dossiers, professor matches, funding dossiers). Data is cached, validated, and only ingested into canonical tables when the user pins/saves it, enabling a consistent dataflow and a clean “source-of-truth” model.

Scraping is not deleted immediately; it becomes an optional fallback behind feature flags.

⸻

2) Problem Statement

Current pain points
	•	Scraping fails or becomes unavailable (token exhaustion, rate limits, blocks).
	•	Sites are heterogeneous, forcing complex parsers and frequent fixes.
	•	Data quality varies (missing fields, ambiguous deadlines/requirements).
	•	Scaling to many users increases cost and fragility.
	•	Security concerns: untrusted HTML ingestion, prompt injection risk, and inconsistent provenance.

What we need
	•	A stable system that can:
	•	generate school recommendations and rich school/program info on-demand
	•	match professors reliably
	•	find funding opportunities tied to saved schools/programs
	•	maintain provenance (citations + timestamps)
	•	scale under concurrent usage with predictable cost
	•	defend against abuse and AI-specific threats

⸻

3) Goals
	1.	Remove scraping as a default dependency for core user flows (recommendations → dossier → professors → funding).
	2.	Introduce structured, citation-backed research artifacts with confidence scoring and validation.
	3.	Build a consistent data lifecycle:
	•	research → cache → user pins → ingest → refresh/maintain
	4.	Implement security controls:
	•	HTTP-level rate limiting
	•	global inflight caps
	•	input validation/sanitization
	•	prompt injection resistance
	•	hallucination mitigation via citations and “unknown” fields
	5.	Keep system observable and operable:
	•	job metrics, cache hit rates, provider error rates
	•	clear failure modes and retry strategy

⸻

4) Non-Goals
	•	Building a complete offline “all schools in the US” database up front.
	•	Scraping Google Scholar (explicitly avoided; policy + reliability risk).
	•	Perfect accuracy guarantee (instead: citations, confidence, and “verify” UX).
	•	Launching new paid tiers (but we will add quota hooks to support them later).

⸻

5) Proposed Solution

Core concept: Research Orchestration + Artifact Store

Guidr becomes a research orchestrator that produces durable artifacts:
	1.	Recommendations Artifact: Dream / Reach-Target / Safety school shortlist
	2.	School Dossier Artifact: requirements, deadlines, links, funding summary
	3.	Professor Matches Artifact: ranked professors + papers + links
	4.	Funding Dossier Artifact: internal + (optional) external opportunities

Artifacts are:
	•	structured JSON under strict schemas
	•	include citations and a field-level evidence map
	•	scored for confidence
	•	cached with TTLs
	•	promoted/staged based on quality gates
	•	ingested into canonical DB tables only when user “pins” or “saves”

Scraping becomes fallback-only
	•	Disabled by default in production
	•	Optional behind a feature flag and only used if:
	•	critical fields lack citations and can’t be repaired
	•	confidence remains below threshold
	•	user requests “verify from official pages”

⸻

6) User Flows (End-to-End)

Flow A: Onboarding → Recommendations
	1.	User signs up.
	2.	Onboarding collects:
	•	degree target (MS/PhD)
	•	research interests and program keywords
	•	geography preferences (country/state/schools)
	•	funding preference
	•	optional uploads (CV, transcript, essays)
	3.	Backend computes a profile hash and requests recommendations.
	4.	Frontend displays categorized shortlist with citations and confidence.

Flow B: Save School → Generate Dossier
	1.	User saves a school from recommendations.
	2.	Backend generates a school dossier:
	•	overview
	•	official links (program/admissions)
	•	requirements + deadlines (citation-required)
	•	funding summary
	3.	Dossier is stored; UI shows “last refreshed”, confidence, and sources.

Flow C: Professors for School/Program
	1.	User visits saved school dossier.
	2.	Backend builds professor matches using API-first scholarly data sources.
	3.	UI shows ranked professors with research overlap and recent papers.
	4.	User can “save professor.”

Flow D: Funding (School-specific and optional external)
	1.	If user wants funding, backend generates funding dossier for saved schools.
	2.	UI shows internal funding types and links.
	3.	Optional: external funding (only if reliably citable and eligible).

⸻

7) System Architecture

Components
	•	API Layer (FastAPI)
	•	auth + onboarding routes
	•	endpoints to start research jobs, fetch artifacts, poll status
	•	Job Orchestrator (LangGraph/LangChain)
	•	runs research → extract → validate → score → promote/stage/repair
	•	Workers (Celery)
	•	separate queues by workload class
	•	Artifact Store (DB + Redis)
	•	DB for durable artifacts, relationships, pinned items
	•	Redis for caching + rate limiting + inflight semaphores
	•	Search (Meilisearch)
	•	indexing pinned schools/professors/funding + user saved items
	•	optional: index artifacts for fast UI search
	•	Scholarly Data APIs
	•	Semantic Scholar + OpenAlex (API-first)

Workload classes (queues)
	•	research_fast: recommendation runs
	•	research_heavy: dossiers (school + funding)
	•	scholarly_api: professor enrichment calls (strict rate limits)

Feature flags
	•	ENABLE_AGENTIC_DOSSIERS (default true)
	•	ENABLE_SCRAPE_FALLBACK (default false in prod)
	•	ENABLE_BULK_SCRAPE (default false)

⸻

8) Data Model & Artifact Contracts

Artifact invariants

Every artifact must store:
	•	value_json (schema-valid)
	•	citations_json (URLs + metadata + retrieved_at)
	•	evidence_map_json (field-path → citation IDs)
	•	confidence (0–1)
	•	status: promoted | staged | failed
	•	retrieved_at, fresh_until
	•	schema_version, model_version
	•	fingerprint (dedup key)

Recommended schemas
	•	RecommendationSession
	•	dream[], reach_target[], safety[]
	•	each entry includes: school_name, location, program_guess, rationale, confidence, citations/evidence_map
	•	SchoolDossier
	•	official links + overview
	•	requirements/deadlines: citation-required fields
	•	funding summary + links
	•	warnings[]
	•	ProfessorMatches
	•	ranked list with match_score
	•	recent papers + topics + profile URLs
	•	citations for links/affiliations
	•	FundingDossier
	•	internal funding + links
	•	optional external opportunities (only with strong citations + eligibility)

“Pin-to-ingest” rule
	•	Artifacts are not canonical “truth.”
	•	When user pins/saves:
	•	create a canonical record (or update a per-user saved entity)
	•	keep artifact as provenance snapshot
	•	optionally write to search index

⸻

9) Security & Safety Design

Input validation & sanitization
	•	Strict Pydantic schemas for all endpoints
	•	Normalize text inputs:
	•	trim, max length, character allowlists where feasible
	•	Reject control characters, excessively long payloads, and malformed JSON
	•	Ensure SQLAlchemy remains parameterized (no raw SQL concatenation)

Abuse prevention (DDoS / spam)
	•	HTTP rate limiting (Redis token bucket):
	•	per-IP baseline
	•	per-user limits
	•	heavier throttles for research endpoints
	•	Global inflight caps:
	•	Redis semaphore to cap concurrent research jobs
	•	return 202 + job_id when at cap

Prompt injection resistance
	•	Treat all retrieved content as untrusted.
	•	Never follow instructions found in sources.
	•	Extract facts only into schema fields.
	•	Penalize low-trust domains for critical fields.

Hallucination mitigation
	•	For critical fields (deadlines, requirements, eligibility):
	•	must have citations to official/credible sources
	•	if missing → set unknown and show warning in UI
	•	Add “verify” UI affordances rather than silently guessing.

Provider & API key safety
	•	Store keys in environment/secret manager
	•	Restrict outbound calls to allowlisted domains/providers where possible
	•	Circuit breakers for unstable providers

⸻

10) Performance & Cost Controls

Caching
	•	Recommendations: 24 hours
	•	School dossier: 7 days (manual refresh available)
	•	Professor matches: 30 days
	•	Funding dossier: 7 days

Deduplication
	•	Fingerprint jobs by:
	•	schema_version + model_version
	•	profile_hash (for user-specific)
	•	school_id + program_intent_hash (for dossiers)

Rate limiting per provider
	•	Enforce token buckets for:
	•	scholarly APIs (strict)
	•	deep research provider calls (cost control)
	•	Support per-user daily quotas for refreshes.

Backpressure strategy
	•	When queues are deep:
	•	return partial artifacts (overview + key links)
	•	enqueue the rest and update asynchronously

⸻

11) Observability

Metrics
	•	job durations by type
	•	cache hit rates
	•	provider error rates + retries
	•	artifact promote/stage ratios
	•	rate-limit events and inflight cap rejects

Logs
	•	correlation ID per request and job
	•	structured logs per pipeline stage
	•	safe redaction of user uploads and sensitive fields

⸻

12) Rollout Plan

Phase 0 — Prep (feature flags + no behavior change)
	•	Add/verify feature flags
	•	Implement missing HTTP rate limiter + inflight cap
	•	Ensure system works with scraping disabled

Phase 1 — Agent-first in staging
	•	Turn on ENABLE_AGENTIC_DOSSIERS
	•	Turn off ENABLE_SCRAPE_FALLBACK
	•	Run synthetic test users end-to-end

Phase 2 — Gradual production rollout
	•	Enable for a subset of users
	•	Monitor:
	•	latency
	•	cost
	•	artifact quality (promote vs stage)
	•	Expand rollout based on stability

Phase 3 — Scraping fallback optional
	•	Only enable if paid Firecrawl capacity exists and needed
	•	Keep fallback restricted to official domains

Rollback: flip feature flags back to previous behavior (if still available) while keeping new security controls.

⸻

13) Risks & Mitigations
	1.	Latency from deep research
	•	mitigate with caching, partial artifacts, queue separation, and streaming/polling UX
	2.	Cost spikes under heavy use
	•	mitigate with per-user quotas, cache keys, dedup, inflight caps, and request throttles
	3.	Incorrect info (deadlines/requirements)
	•	mitigate with citation enforcement and “unknown + verify” instead of guessing
	4.	Prompt injection via web sources
	•	mitigate with strict extraction + untrusted-content rules + domain trust scoring
	5.	Provider instability
	•	mitigate with retries, circuit breakers, fallback modes, and graceful UI errors

⸻

14) Open Questions — Resolved

All open questions were resolved during implementation (2026-03-26):

| # | Question | Decision |
|---|----------|----------|
| 1 | External funding in v1? | **Yes** — external fellowships (NSF GRFP, NIH F31, NDSEG, Hertz, Ford Foundation, Fulbright) included in funding dossier, filtered by `country_of_citizenship` and `primary_field_of_study` |
| 2 | Trusted domain policy? | **5-tier broader policy**: 1.0 official entity domain, 0.8 known aggregators (usnews/niche/petersons/gradschools), 0.7 .edu/.gov (non-entity), 0.5 general reputable (wikipedia/bloomberg/reuters), 0.3 other URL, 0.0 no URL |
| 3 | Global vs per-user dossiers? | **Per-user** — `enrichment_cache` has `user_id` FK (nullable); lookup tries per-user first, falls back to global. Fingerprint includes `user_id_hash`. |
| 4 | UI pattern for staged artifacts? | **Confidence badges** on InstitutionCard/ProgramCard: ≥0.78 auto-promoted (no badge), 0.55–0.77 staged with amber badge, <0.55 shown with “unverified — verify with school” warning. No automatic repair (on-demand / paid tier only). |
| 5 | Per-user quotas? | **50 enrichments/day** on free tier (Redis token bucket). Admins bypass via `X-Internal-Key`. |

**Final confidence thresholds implemented:**
- Auto-promote: ≥ 0.78 (was 0.85 in original draft)
- Stage: 0.55 – 0.77 (was 0.70 – 0.84)
- Warn (no auto-repair): < 0.55 (was < 0.70 with auto-repair)

**Final cache TTLs implemented** (updated from draft):
- Recommendations: 7 days (was 24 hours)
- School dossier: 30 days (was 7 days)
- Professor matches: 30 days (unchanged)
- Funding dossier: 14 days (was 7 days)

⸻

15) Decision

Adopt the Agentic Research Pivot:
	•	Agent-first dossier generation for core flows
	•	Scraping disabled by default and retained only as optional fallback
	•	Add security controls (HTTP rate limiting + inflight caps) as required for launch

⸻
