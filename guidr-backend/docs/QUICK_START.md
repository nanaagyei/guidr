# Quick Start: Guidr Agentic Research Pipeline

Get the full agentic research pipeline running and producing personalised results for a user in under 15 minutes.

---

## 1. Start Infrastructure

```bash
docker-compose up -d
```

Starts PostgreSQL (5433), Redis (6379), Meilisearch (7700), MinIO (9000/9001), and Celery workers.

## 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` — minimum required keys:

```bash
# --- Server ---
DATABASE_URL=postgresql://guidr_user:guidr_password@localhost:5433/guidr_db
JWT_SECRET=change-me-to-a-long-random-string
INTERNAL_API_KEY=<generate below>

# --- Agentic Research (primary, recommended) ---
PERPLEXITY_API_KEY=pplx-your-key     # https://www.perplexity.ai/settings/api
                                      # Omit for dev — falls back to stub provider

# --- Foundation Data ---
COLLEGE_SCORECARD_API_KEY=your-key   # https://api.data.gov/signup/

# --- Professor Matching (optional but recommended) ---
SEMANTIC_SCHOLAR_API_KEY=your-key    # https://www.semanticscholar.org/product/api
# OpenAlex is free — no key required

# --- Email (required for user registration) ---
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password  # Gmail App Password, not account password

# --- Scraping fallback (disabled by default) ---
# ENABLE_SCRAPE_FALLBACK=false
# FIRECRAWL_API_KEY=fc-your-key        # Only if you enable scraping fallback
```

Generate your internal API key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 3. Start the Server

```bash
python run.py
```

Migrations run automatically on startup. The server starts on `http://localhost:8000`.

Verify:
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## 4. Load Foundation Data

This loads basic school metadata (name, city, type) from the College Scorecard API.
Detailed content (requirements, deadlines, funding) comes from the agentic pipeline later.

```bash
# All US graduate schools (async — recommended)
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"async_run": true}'

# Small batch for local testing
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"state": "MA", "limit": 10}'
```

Note a school ID from the response:
```bash
curl "http://localhost:8000/schools?name=MIT" \
  -H "X-Internal-Key: $INTERNAL_API_KEY"
# Copy the `id` field — you'll use SCHOOL_ID below
```

## 5. Register a Test User

```bash
# Step 1 — Send 2FA code
curl -X POST http://localhost:8000/auth/2fa/send \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "purpose": "register"}'

# Step 2 — Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User",
    "verification_code": "123456"
  }'
```

Log in to get a session cookie:
```bash
curl -c cookies.txt -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!"}'
```

Use `-b cookies.txt` for all subsequent user-facing requests.

## 6. Set Up User Profile

Profile data personalises every agentic research call. The more complete the profile, the better the recommendations, professor matches, and funding opportunities.

```bash
curl -X PUT http://localhost:8000/profile \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{
    "intended_degree": "phd",
    "primary_field_of_study": "Computer Science",
    "research_areas": ["Machine Learning", "Natural Language Processing"],
    "career_goals": "Research scientist focused on language model safety",
    "preferred_countries": ["USA"],
    "preferred_cities": ["Boston", "Cambridge"],
    "funding_priority": "must_have",
    "program_style_preference": "research",
    "country_of_citizenship": "US"
  }'
```

**Frontend equivalent**: Onboarding Wizard steps 2–5, or **Settings → Application Settings**.

Key profile fields used by the pipeline:

| Field | Used by |
|-------|---------|
| `research_areas` | Professor matching (OpenAlex keywords), funding eligibility, recommendation rationale |
| `primary_field_of_study` | All dossier prompts, external funding selection |
| `country_of_citizenship` | External fellowship filtering (NSF, NIH, Fulbright, etc.) |
| `funding_priority` | Recommendation tier weighting |
| `preferred_countries` / `preferred_cities` | Recommendation geography filtering |

## 7. Request AI Recommendations

```bash
# Trigger (async)
curl -X POST http://localhost:8000/recommendations/request \
  -b cookies.txt
# Returns: {"job_id": "...", "status": "queued"}

# Poll
curl http://localhost:8000/pipeline/jobs/<job_id> \
  -b cookies.txt
# Wait for "status": "completed"

# Read results
curl http://localhost:8000/recommendations/latest \
  -b cookies.txt
```

**Response structure:**
```json
{
  "status": "promoted",
  "confidence": 0.84,
  "dream": [
    {
      "school_name": "MIT",
      "location": "Cambridge, MA",
      "program_guess": "PhD in Computer Science",
      "rationale": "World-leading NLP/ML labs; strong NSF fellowship placement",
      "confidence": 0.90,
      "citations": ["[c1] https://www.csail.mit.edu/"]
    }
  ],
  "reach_target": [...],
  "safety": [...]
}
```

**Frontend**: Results populate the `Recommended Schools Tile` and `Applied Schools Tile` on the dashboard.

## 8. Research a School (Dossier)

```bash
SCHOOL_ID=<uuid-from-step-4>

# Request (async)
curl -X POST "http://localhost:8000/dossiers/schools/$SCHOOL_ID/research" \
  -b cookies.txt

# Poll job, then read value
curl "http://localhost:8000/pipeline/cache/value?entity_kind=school_dossier&entity_id=$SCHOOL_ID" \
  -b cookies.txt
```

**Dossier includes:**
- Admission requirements (GPA, GRE, letters of recommendation)
- Application deadlines per cycle
- Official links (admissions page, graduate catalog)
- Funding summary
- `confidence` score, `warnings[]` for unverified fields, full `citations_json`

A dossier with `confidence >= 0.78` is auto-promoted. Between 0.55–0.77 it is staged with a confidence badge. Below 0.55 it is shown with an "unverified — verify with school" warning. **No automatic repair** — repair is on-demand only.

## 9. Match Professors

```bash
# Request (uses research_areas from profile automatically)
curl -X POST "http://localhost:8000/dossiers/schools/$SCHOOL_ID/professors/match" \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{}'

# Get all professor matches across your saved schools
curl http://localhost:8000/dossiers/professors/recommended \
  -b cookies.txt
```

The professor graph:
1. **OpenAlex** — searches authors affiliated with the school by research keywords (up to 5 interests, 25 candidates)
2. **Semantic Scholar** — enriches with h-index, recent papers, citation counts (batch up to 20, rate-limited to 1 req/s)
3. **Perplexity synthesis** — ranks by research overlap with the user and adds accepting-students status

**Frontend**: Results populate the `Professors Tile` on the dashboard.

## 10. Get the Funding Dossier

```bash
curl -X POST "http://localhost:8000/dossiers/schools/$SCHOOL_ID/funding/research" \
  -b cookies.txt
```

The funding dossier returns **two sections**:

**`funding_opportunities`** — internal institutional funding:
- TA/RA assistantships, fellowships, merit scholarships
- `covers_tuition`, `covers_stipend`, `covers_health_insurance` flags
- Application deadlines and eligibility criteria

**`external_opportunities`** — national fellowships matched to the user's field and citizenship:

| Example | Field | Citizenship |
|---------|-------|-------------|
| NSF GRFP | STEM | US citizens/nationals |
| NIH F31 | Biomedical | US citizens/nationals |
| NDSEG | Engineering/science | US citizens |
| Hertz Fellowship | Applied science | US citizens |
| Ford Foundation | Any | US citizens |
| Fulbright | Any | Varies by country |

All external opportunities include official application URLs and eligibility notes.

## 11. View Application Deadlines

```bash
curl http://localhost:8000/dossiers/deadlines \
  -b cookies.txt
```

Returns deadlines extracted from all school dossiers you've requested. The `is_verified` flag is `false` for deadlines with low citation confidence — the frontend shows a warning.

**Frontend**: The `Calendar Tile` reads from this endpoint and computes urgency (Urgent = ≤7 days, Soon = ≤21 days, Upcoming = further) from the deadline date.

---

## Authentication Summary

| Caller | Auth method | Header / Cookie |
|--------|------------|-----------------|
| Scripts / CI / cron | Internal API key | `X-Internal-Key: <key>` |
| Admin user | Session cookie | Set by login |
| Regular user | Session cookie | Set by login |

- `/ingestion/*` and `/pipeline/admin/*` — admin session OR `X-Internal-Key`
- `/dossiers/*`, `/recommendations/*`, `/pipeline/enrich` — logged-in user session only

---

## Monitor Jobs

```bash
# All pipeline jobs (admin)
curl http://localhost:8000/ingestion/pipeline/jobs \
  -H "X-Internal-Key: $INTERNAL_API_KEY"

# Specific job (user)
curl http://localhost:8000/pipeline/jobs/<job_id> \
  -b cookies.txt

# Domain health (admin)
curl http://localhost:8000/pipeline/admin/domains \
  -H "X-Internal-Key: $INTERNAL_API_KEY"
```

---

## Verify Results in Python

```python
from src.db import SessionLocal
from src.models.institution import Institution
from src.models.enrichment_cache import EnrichmentCache

db = SessionLocal()

# Check enriched schools
for school in db.query(Institution).limit(5).all():
    print(f"{school.name}: enriched={school.last_enriched_at}, "
          f"confidence={school.last_enrichment_confidence}")

# Check dossier cache
cache_entries = db.query(EnrichmentCache).filter(
    EnrichmentCache.entity_kind == "school_dossier"
).limit(5).all()
for entry in cache_entries:
    print(f"school_id={entry.entity_id}, confidence={entry.confidence}, "
          f"status={entry.status}, user_id={entry.user_id}")

db.close()
```

---

## Reset and Reload

```bash
python scripts/reset_data.py --dry-run   # Preview what will be deleted
python scripts/reset_data.py --yes       # Execute reset

# Reload foundation data
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "X-Internal-Key: $INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"async_run": true}'
```

---

## Frontend ↔ API Mapping

| User Action in UI | API Endpoint Called | Dashboard Tile |
|-------------------|---------------------|----------------|
| Complete onboarding wizard | `PUT /profile` | Profile Completion |
| Dashboard load | `GET /recommendations/latest` | Recommended Schools |
| Dashboard load | `GET /schools/saved` | Saved Schools |
| Dashboard load | `GET /dossiers/professors/recommended` | Professors |
| Dashboard load | `GET /dossiers/deadlines` | Upcoming Deadlines |
| Click school → request dossier | `POST /dossiers/schools/{id}/research` | (async, then InstitutionCard) |
| Settings → save research areas | `PUT /profile` | (updates all future research) |

All dashboard tiles load **independently in parallel** with skeleton loaders — no full-page blocking.

---

## Next Steps

- **[Pipeline Guide](PIPELINE_GUIDE.md)** — Full architecture, all endpoints, DossierGraph internals, confidence scoring
- **[Integration Summary](INTEGRATION_SUMMARY.md)** — How all components work together
- **[Enrichment Verification](ENRICHMENT_PIPELINE_VERIFICATION.md)** — End-to-end smoke tests
- **[R2 Setup](R2_SETUP.md)** — Cloudflare R2 for production document storage
- MinIO console: http://localhost:9001
