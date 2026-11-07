# Guidr Roadmap

> Updated 2026-11-07. The forward plan no longer lives in this file.

Guidr is being repositioned as an advisor-led, verified application workflow for applicants to
funded research degrees. See:

- **`docs/POSITIONING.md`**: who Guidr is for, the core promise, the stage plan and gates, the
  do-not-build list, and what "verified" means.
- **The GitHub issue backlog** (#37–#80), staged by labels `stage-0` … `stage-3`, with gate issues
  #72 (Stage 0 exit), #74 (Stage 1 exit) and #76 (Stage 2 exit).

The milestone list that used to be here (search, documents, essay review, recommendations,
professors, private beta, pipeline at scale, and a post-MVP wish list) is superseded by that
backlog. It remains in git history.

---

## History: completed milestones

## Milestone 0: Project Bootstrapping & Foundations
**Status:** ✅ Complete

Set up both backend and frontend repositories with basic infrastructure, CI pipelines, and documentation.

**Delivered:**
- Next.js App Router + TypeScript frontend with shadcn/ui design system (since upgraded to Next.js 15)
- FastAPI + PostgreSQL + Redis + Celery + Meilisearch backend
- Docker Compose services (postgres, redis, meilisearch, minio, celery-worker, celery-beat)
- Alembic migrations (001–015), GitHub Actions CI

---

## Milestone 1: Authentication & App Shell
**Status:** ✅ Complete

Implement user registration, login, JWT authentication, and basic dashboard shell.

**Delivered:**
- Email/password registration and login with JWT access tokens
- Emailed verification codes for registration and password reset (sign-in has no second factor)
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
