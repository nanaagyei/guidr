# Quick Start: Data Collection & Pipeline

Get started with data collection and the scraping pipeline in 5 minutes.

## Prerequisites

1. **Start Docker services**:
```bash
docker-compose up -d
```

2. **Set environment variables** in `.env`:
```bash
COLLEGE_SCORECARD_API_KEY=your_key_here   # api.data.gov
FIRECRAWL_API_KEY=your_key_here           # firecrawl.dev
GROQ_API_KEY=your_key_here                # or OPENAI_API_KEY (for LLM extraction)
```

3. **Run migrations**:
```bash
alembic upgrade head
```

4. **(Optional) Install Playwright** (for agent-based collection):
```bash
playwright install chromium
```

## Step 0: Reset and Load Foundation Data (Optional)

To start from a clean slate and reload from College Scorecard:

```bash
python scripts/reset_pipeline_data.py --dry-run   # Preview what would be deleted
python scripts/reset_pipeline_data.py --yes       # Wipe schools, programs, faculty, funding

python scripts/load_scorecard_schools.py          # Load all US graduate schools
python scripts/load_scorecard_schools.py --limit 50   # Or a small batch for testing
```

## Step 1: Load Foundation Data (Pipeline)

Load graduate schools from College Scorecard:

```bash
# Start API server
uvicorn src.main:app --reload --port 8000

# Load schools (replace <token> with admin JWT)
curl -X POST http://localhost:8000/ingestion/schools/scorecard/load \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"state": "CA", "limit": 20}'
```

## Step 2: Run Scraping Pipeline

Trigger the pipeline for an institution (overview, programs, faculty, funding):

```bash
# Get an institution ID from the database, then:
curl -X POST http://localhost:8000/ingestion/pipeline/run \
  -H "Authorization: Bearer <token>" \
  -d '{"institution_id": "<uuid>"}'
```

## Step 3: Agent-Based Collection (Alternative)

Test the agent system with 3 schools:

```bash
python -m scripts.quick_start_data_collection
```

This will:
- Fetch 3 top schools
- Collect school data (description, acceptance rate, tuition)
- Discover programs for each school
- Show you what data was collected

## Step 4: Small Batch Collection

Collect data for 10 schools:

```bash
python -m scripts.comprehensive_data_collection --max-schools 10 --max-programs 15
```

This will:
- Fetch 10 schools from multiple sources
- Collect comprehensive data for each
- Discover and collect program data
- Save everything to the database
- Show quality metrics

## Step 3: Review Results

Check what was collected:

```python
from src.db import SessionLocal
from src.models.institution import Institution
from src.models.program import Program

db = SessionLocal()
schools = db.query(Institution).limit(10).all()
for school in schools:
    programs = db.query(Program).filter(Program.institution_id == school.id).all()
    print(f"{school.name}: {len(programs)} programs, completeness: {school.data_completeness_score}%")
```

## Step 6: Scale Up

Once you're confident, scale to more schools:

```bash
# 50 schools
python -m scripts.comprehensive_data_collection --max-schools 50

# 100 schools
python -m scripts.comprehensive_data_collection --max-schools 100
```

## Using Background Jobs

For larger batches, use Celery workers:

```bash
# Start worker (in separate terminal)
celery -A src.workers.celery_app worker --loglevel=info

# Queue jobs from Python
python
>>> from src.workers.scraper_worker import collect_school_comprehensive_task
>>> task = collect_school_comprehensive_task.delay("institution-uuid")
>>> print(f"Job ID: {task.id}")
```

## Common Issues

**Playwright not found**: Run `playwright install chromium`

**No API keys**: Set `GROQ_API_KEY` or `OPENAI_API_KEY` in `.env`

**Rate limits**: The system automatically falls back to alternative methods

**Memory issues**: Process schools in smaller batches (use `--max-schools`)

## Next Steps

- **[Pipeline Guide](PIPELINE_GUIDE.md)** – Full pipeline architecture, data flow, troubleshooting
- [Comprehensive Data Collection Guide](COMPREHENSIVE_DATA_COLLECTION_GUIDE.md) – Agent-based collection
- Check scrape jobs: `GET /ingestion/pipeline/jobs`
- MinIO console (raw data): http://localhost:9001
- Set up scheduled jobs via Celery Beat (runs automatically with docker-compose)

