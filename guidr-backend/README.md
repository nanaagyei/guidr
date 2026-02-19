# Guidr Backend

Backend API for Guidr - A graduate school application platform.

## Tech Stack

- **Framework:** FastAPI
- **Language:** Python 3.11+
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Queue:** Redis (for async workers)
- **Background jobs:** Celery
- **Search:** Meilisearch
- **Scraping/LLM:** Scrapy, Playwright, LangChain/Groq/OpenAI

## Setup

### Quick Start with Docker

1. **Start all services with Docker:**
   ```bash
   docker-compose up -d
   ```
   This starts PostgreSQL (5433), Redis (6379), Meilisearch (7700), MinIO (9000/9001), Celery worker, and Celery Beat.

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   Install Playwright browsers once (required for scraping flows):
   ```bash
   python -m playwright install chromium
   ```

3. **Set up environment variables:**
   Copy `.env.example` to `.env` and adjust secrets:
   ```bash
   cp .env.example .env
   ```
   Generate a JWT secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   
   **Note:** For Gmail, you need to create an App Password:
   1. Go to your Google Account settings
   2. Enable 2-Step Verification
   3. Go to App Passwords and generate one for "Mail"
   4. Use that password as `SMTP_PASSWORD`
   
   **Note:** For Cloudflare R2 setup, see [R2 Setup Guide](./docs/R2_SETUP.md) for detailed instructions. You only need S3 API credentials (Access Key ID and Secret Access Key) - no Account API Token or User API Token required.

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **(Optional) Seed initial data:**
   ```bash
   python scripts/seed_data.py
   # or use live APIs for richer data
    python scripts/seed_from_apis.py --year 2022 --limit 250
   ```

6. **Start the development server:**
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

7. **Access the API:**
   - API: http://localhost:8000
   - Health check: http://localhost:8000/
   - API docs: http://localhost:8000/docs

### Data ingestion & background workers

- **College Scorecard bulk load** (foundation data):
  ```bash
  # Load graduate schools (requires COLLEGE_SCORECARD_API_KEY)
  curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
    -H "Authorization: Bearer <admin-token>" \
    -d '{"state": "CA", "limit": 50}'
  ```
- **IPEDS ingestion**:
  ```bash
  curl -X POST http://localhost:8000/ingestion/schools/ipeds -H "Authorization: Bearer <token>" -d '{"year": "2022", "limit": 500}'
  ```
- **Enrich with Scorecard financials** (existing institutions):
  ```bash
  curl -X POST http://localhost:8000/ingestion/schools/scorecard -H "Authorization: Bearer <token>"
  ```
- **Scraping pipeline** (overview, programs, faculty, funding):
  ```bash
  curl -X POST http://localhost:8000/ingestion/pipeline/run -H "Authorization: Bearer <token>" -d '{"institution_id": "<uuid>"}'
  ```
- **Reindex Meilisearch**:
  ```bash
  python scripts/reindex_search.py
  ```

### Pipeline documentation

- **[Pipeline Guide](docs/PIPELINE_GUIDE.md)** – Architecture, setup, data flow, API endpoints
- **Data zones**: Raw (MinIO) → Staging (PostgreSQL) → Production (PostgreSQL)

### Comprehensive Data Collection System

We now have a robust, multi-layered data collection system that combines:
- **Firecrawl API** for structured web scraping
- **LLM-powered agents** for intelligent navigation and extraction
- **Playwright** for dynamic content and JavaScript-rendered pages
- **Google Search integration** for finding school information

**Quick Start**:
```bash
# Test with 3 schools
python -m scripts.quick_start_data_collection

# Collect data for 50 schools
python -m scripts.comprehensive_data_collection --max-schools 50 --max-programs 20
```

**Documentation**:
- 📖 [Full Guide](docs/COMPREHENSIVE_DATA_COLLECTION_GUIDE.md) - Complete usage guide
- 🚀 [Quick Start](docs/QUICK_START.md) - Get started in 5 minutes

**Features**:
- Multi-source school discovery (IPEDS, rankings, curated lists)
- Comprehensive school data collection (description, acceptance rate, tuition, funding)
- Intelligent program discovery (handles different website layouts)
- Multi-method program extraction (Firecrawl → LLM → Playwright fallback)
- Data quality tracking and validation
- Background job support via Celery

### Docker Commands

- **Start services:** `docker-compose up -d`
- **Stop services:** `docker-compose down`
- **View logs:** `docker-compose logs -f`
- **Reset database (WARNING: deletes all data):** `docker-compose down -v` then `docker-compose up -d`

### Manual Setup (without Docker)

If you prefer to run PostgreSQL and Redis manually, update the `DATABASE_URL` and `REDIS_URL` in your `.env` file accordingly.

## Project Structure

```
guidr-backend/
├── src/
│   ├── main.py          # FastAPI app
│   ├── config.py        # Configuration
│   ├── db.py            # Database setup
│   ├── models/          # SQLAlchemy models
│   ├── routes/          # API routes
│   ├── pipeline/        # Data pipeline
│   │   ├── clients/     # Firecrawl, MinIO/S3
│   │   ├── extractors/  # Funding, faculty, program, overview
│   │   ├── processors/  # Validator, transformer, enricher
│   │   ├── scraping/    # Orchestrator, URL discovery
│   │   ├── schemas/     # Pydantic validation
│   │   └── tasks/       # Celery pipeline tasks
│   ├── dependencies/    # FastAPI dependencies
│   ├── utils/           # Utility functions
│   └── workers/         # Celery workers
├── docs/
│   ├── PIPELINE_GUIDE.md
│   ├── COMPREHENSIVE_DATA_COLLECTION_GUIDE.md
│   └── QUICK_START.md
├── alembic/             # Database migrations
├── docker-compose.yml   # Docker services
├── requirements.txt
└── .env.example
```

## Development

- **Linting:** `flake8 src`
- **Tests:** `pytest`
- **Migrations:** `alembic revision --autogenerate -m "description"`

## CI/CD

GitHub Actions workflow runs on push/PR to main/dev branches:
- Linting (flake8)
- Tests (pytest)

![Backend CI](https://github.com/nanaagyei/guidr-backend/actions/workflows/backend-ci.yml/badge.svg)

