# Comprehensive Data Collection System - Usage Guide

This guide explains how to use the agent-based data collection system that combines Firecrawl, LLM agents, Playwright, and Google search.

**See also:** [Pipeline Guide](PIPELINE_GUIDE.md) for the orchestrated scraping pipeline (overview, programs, faculty, funding) via API and Celery.

## Table of Contents

1. [Prerequisites & Installation](#prerequisites--installation)
2. [Configuration](#configuration)
3. [Component Overview](#component-overview)
4. [Usage Examples](#usage-examples)
5. [Integration with Existing System](#integration-with-existing-system)
6. [Running the Batch Script](#running-the-batch-script)
7. [Using Worker Jobs](#using-worker-jobs)
8. [Troubleshooting](#troubleshooting)

## Prerequisites & Installation

### 1. Install Required Dependencies

Add these to your `requirements.txt` if not already present:

```bash
# Browser automation
playwright==1.40.0

# Already included but verify:
httpx==0.25.2
beautifulsoup4==4.12.2
groq  # or openai for LLM
```

Install Playwright browsers:

```bash
playwright install chromium
```

### 2. Environment Variables

Add these to your `.env` file:

```bash
# Existing
FIRECRAWL_API_KEY=your_firecrawl_key
GROQ_API_KEY=your_groq_key  # or OPENAI_API_KEY
COLLEGE_SCORECARD_API_KEY=your_scorecard_key

# New additions
GOOGLE_SEARCH_ENABLED=true
PLAYWRIGHT_BROWSER=headless  # headless, chromium, or firefox
PLAYWRIGHT_TIMEOUT=30000
FIRECRAWL_EXTRACTION_SCHEMA=true
AGENT_MAX_STEPS=10
AGENT_RETRY_ATTEMPTS=3
```

## Configuration

The system uses a layered approach with fallbacks:

1. **Primary**: Firecrawl (fastest, most reliable)
2. **Secondary**: LLM agents (handles complex layouts)
3. **Tertiary**: Playwright (for dynamic JavaScript content)
4. **Fallback**: Google search (when URLs aren't available)

## Component Overview

### 1. Multi-Source School Fetcher

Aggregates schools from multiple sources (IPEDS, top schools, rankings).

**Location**: `src/scrapers/schools/multi_source_fetcher.py`

**Usage**:
```python
from src.scrapers.schools.multi_source_fetcher import MultiSourceFetcher

fetcher = MultiSourceFetcher()
schools = await fetcher.fetch_all_schools(limit=500)
# Returns: List[InstitutionSeed]
```

### 2. Google Search Agent

Finds school websites and program pages via Google search.

**Location**: `src/scrapers/agents/google_search_agent.py`

**Usage**:
```python
from src.scrapers.agents.google_search_agent import GoogleSearchAgent

agent = GoogleSearchAgent()
website = await agent.find_school_website("MIT", "USA")
programs_page = await agent.find_programs_page("MIT", website)
```

### 3. Comprehensive School Collector

Collects all school information (description, acceptance rate, tuition, funding).

**Location**: `src/scrapers/schools/comprehensive_collector.py`

**Usage**:
```python
from src.scrapers.schools.comprehensive_collector import ComprehensiveSchoolCollector

collector = ComprehensiveSchoolCollector()
data = await collector.collect_school_data(
    institution_name="Massachusetts Institute of Technology",
    website_url="https://www.mit.edu"
)
# Returns: Dict with description, acceptance_rate, tuition, funding_opportunities, etc.
```

### 4. Program Discovery Agent

Finds all graduate programs for a school.

**Location**: `src/scrapers/agents/program_discovery_agent.py`

**Usage**:
```python
from src.scrapers.agents.program_discovery_agent import ProgramDiscoveryAgent

agent = ProgramDiscoveryAgent()
program_urls = await agent.discover_programs(
    institution_name="MIT",
    institution_url="https://www.mit.edu"
)
# Returns: List[str] of program URLs
```

### 5. Program Collection Agent

Collects detailed program information.

**Location**: `src/scrapers/agents/program_collection_agent.py`

**Usage**:
```python
from src.scrapers.agents.program_collection_agent import ProgramCollectionAgent
from src.models.institution import Institution

agent = ProgramCollectionAgent()
program_seed = await agent.collect_program_data(
    program_url="https://www.mit.edu/program/computer-science",
    institution=institution  # Institution model object
)
# Returns: ProgramSeed
```

### 6. Playwright Scraper

Handles dynamic JavaScript-rendered pages.

**Location**: `src/scrapers/browser/playwright_scraper.py`

**Usage**:
```python
from src.scrapers.browser.playwright_scraper import PlaywrightScraper

scraper = PlaywrightScraper()
data = await scraper.scrape_dynamic_page("https://example.com/dynamic-page")
# Returns: Dict with extracted data
```

## Usage Examples

### Example 1: Collect Data for a Single School

```python
import asyncio
from src.db import SessionLocal
from src.scrapers.schools.comprehensive_collector import ComprehensiveSchoolCollector
from src.scrapers.agents.program_discovery_agent import ProgramDiscoveryAgent
from src.scrapers.agents.program_collection_agent import ProgramCollectionAgent
from src.services.data_ingestion import DataIngestionService
from src.models.institution import Institution

async def collect_school_data(school_name: str, website_url: str):
    db = SessionLocal()
    try:
        # Initialize collectors
        school_collector = ComprehensiveSchoolCollector()
        program_discovery = ProgramDiscoveryAgent()
        program_collection = ProgramCollectionAgent()
        ingestion_service = DataIngestionService(db)
        
        # 1. Collect school data
        school_data = await school_collector.collect_school_data(
            school_name, website_url
        )
        
        # 2. Get or create institution
        institution = db.query(Institution).filter(
            Institution.name == school_name
        ).first()
        
        if not institution:
            # Create from seed (you'd need to convert school_data to InstitutionSeed)
            # For now, assume it exists
            pass
        
        # Update institution with collected data
        if school_data.get("description"):
            institution.description = school_data["description"]
        db.commit()
        
        # 3. Discover programs
        program_urls = await program_discovery.discover_programs(
            school_name, website_url
        )
        
        # 4. Collect program data
        for program_url in program_urls[:10]:  # Limit to 10
            program_seed = await program_collection.collect_program_data(
                program_url, institution
            )
            
            # Save to database
            program = ingestion_service.ingest_program(program_seed, institution.id)
            db.commit()
        
        # Cleanup
        await school_collector.close()
        await program_discovery.close()
        await program_collection.close()
        
    finally:
        db.close()

# Run it
asyncio.run(collect_school_data("MIT", "https://www.mit.edu"))
```

### Example 2: Use the Batch Script

The easiest way to collect data for multiple schools:

```bash
# Collect data for top 50 schools, max 20 programs each
python -m scripts.comprehensive_data_collection \
    --max-schools 50 \
    --max-programs 20 \
    --skip-existing

# Collect data for top 100 schools, all programs
python -m scripts.comprehensive_data_collection \
    --max-schools 100 \
    --max-programs 50
```

### Example 3: Use Worker Jobs (Celery)

Queue jobs for background processing:

```python
from src.workers.scraper_worker import (
    collect_school_comprehensive_task,
    discover_programs_task,
    collect_program_comprehensive_task
)

# Collect comprehensive school data
result = collect_school_comprehensive_task.delay(institution_id="uuid-here")

# Discover programs
result = discover_programs_task.delay(institution_id="uuid-here")

# Collect program data
result = collect_program_comprehensive_task.delay(
    program_url="https://...",
    institution_id="uuid-here"
)
```

## Integration with Existing System

### 1. Update Existing Seed Scripts

Your existing `scripts/batch_seed.py` can now use the new components:

```python
from src.scrapers.schools.multi_source_fetcher import MultiSourceFetcher

# Instead of just IPEDS, use multi-source fetcher
fetcher = MultiSourceFetcher()
schools = await fetcher.fetch_all_schools(limit=500)
```

### 2. Enhance Data Ingestion Service

The `DataIngestionService` already works with the new components. You can enhance it:

```python
from src.scrapers.schools.comprehensive_collector import ComprehensiveSchoolCollector

class DataIngestionService:
    def enrich_institution_comprehensive(self, institution_id: str):
        """Enrich institution with comprehensive data."""
        collector = ComprehensiveSchoolCollector()
        # ... use collector to get comprehensive data
```

### 3. Use with Existing Routes

You can add new API endpoints:

```python
# In src/routes/data_ingestion.py
from fastapi import APIRouter, Depends
from src.workers.scraper_worker import collect_school_comprehensive_task

router = APIRouter()

@router.post("/schools/{institution_id}/collect-comprehensive")
async def collect_school_comprehensive(
    institution_id: str,
    db: Session = Depends(get_db)
):
    """Trigger comprehensive data collection for a school."""
    task = collect_school_comprehensive_task.delay(institution_id)
    return {"job_id": task.id, "status": "queued"}
```

## Running the Batch Script

### Basic Usage

```bash
cd guidr-backend
python -m scripts.comprehensive_data_collection --max-schools 50
```

### Options

- `--max-schools`: Maximum number of schools to process (default: 100)
- `--max-programs`: Maximum programs per school (default: 20)
- `--skip-existing`: Skip schools that already have programs

### Output

The script will:
1. Fetch schools from multiple sources
2. Collect comprehensive data for each school
3. Discover all programs
4. Collect program data
5. Save to database
6. Print quality metrics summary

Example output:
```
Step 1: Fetching top 50 schools from multiple sources...
Discovered 50 schools
Step 2: Collecting comprehensive school data...
Processing school 1/50: MIT
  Discovering programs for MIT...
  Found 25 programs
  Collecting data for 20 programs...
...
============================================================
Collection Summary:
  Schools discovered: 50
  Schools collected: 48
  Programs discovered: 450
  Programs collected: 380
  Overall success rate: 84.44%
  Average completeness: 72.5
  Errors: 5
============================================================
```

## Using Worker Jobs

### Setup Celery Worker

Make sure Celery worker is running:

```bash
celery -A src.workers.celery_app worker --loglevel=info
```

### Queue Jobs Programmatically

```python
from src.workers.scraper_worker import (
    collect_school_comprehensive_task,
    discover_programs_task,
    collect_program_comprehensive_task
)

# Collect school data
task = collect_school_comprehensive_task.delay("institution-uuid")
print(f"Job ID: {task.id}")

# Check status
print(f"Status: {task.status}")
print(f"Result: {task.result}")
```

### Queue Jobs from API

```python
@router.post("/schools/{institution_id}/collect")
async def trigger_collection(institution_id: str):
    task = collect_school_comprehensive_task.delay(institution_id)
    return {"job_id": task.id}
```

## Data Quality Tracking

The system automatically tracks data quality metrics:

```python
from src.utils.data_quality import get_tracker

tracker = get_tracker()
summary = tracker.get_summary()

print(f"Success rate: {summary['overall_success_rate']:.2%}")
print(f"Average completeness: {summary['average_completeness_score']:.1f}")
print(f"Method success rates: {summary['method_success_rates']}")
```

## Troubleshooting

### Issue: Playwright not working

**Solution**: Install Playwright browsers:
```bash
playwright install chromium
```

### Issue: Google search not finding websites

**Solution**: 
- The Google search agent uses web scraping, which may be blocked
- Consider using the `GOOGLE_SEARCH_API_KEY` if you have Google Custom Search API access
- Or provide website URLs directly

### Issue: LLM extraction failing

**Solution**:
- Check that `GROQ_API_KEY` or `OPENAI_API_KEY` is set
- Verify `ENABLE_LLM_EXTRACTION=true` in config
- Check API rate limits

### Issue: Firecrawl rate limits

**Solution**:
- Firecrawl has rate limits based on your plan
- The system will fall back to LLM agents and Playwright
- Consider adding delays between requests

### Issue: Memory issues with Playwright

**Solution**:
- Playwright can be memory-intensive
- Close browsers properly: `await scraper.close()`
- Process schools in smaller batches

### Issue: Duplicate programs

**Solution**:
- The validator includes duplicate detection
- Use `detect_duplicates()` function before saving
- Check `data_completeness_score` to identify incomplete records

## Best Practices

1. **Start Small**: Test with 5-10 schools first
2. **Monitor Quality**: Check data quality metrics regularly
3. **Handle Errors**: The system logs errors - review them
4. **Rate Limiting**: Be respectful of website rate limits
5. **Incremental Updates**: Use `--skip-existing` to avoid re-scraping
6. **Background Jobs**: Use Celery for large batches
7. **Validation**: Always validate data before saving

## Next Steps

1. Run a small test batch: `python -m scripts.comprehensive_data_collection --max-schools 5`
2. Review the collected data quality
3. Adjust extraction methods if needed
4. Scale up to larger batches
5. Set up scheduled jobs for regular updates

## Support

For issues or questions:
- Check logs in `guidr-backend/logs/`
- Review data quality metrics
- Check individual component documentation
- Review error messages in the output

