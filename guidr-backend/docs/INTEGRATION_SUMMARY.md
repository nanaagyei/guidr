# Integration Summary: How the New Components Work Together

This document explains how all the new data collection components integrate with your existing system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Collection Flow                     │
└─────────────────────────────────────────────────────────────┘

1. School Discovery
   ├─ MultiSourceFetcher (aggregates from IPEDS, rankings, etc.)
   └─ GoogleSearchAgent (finds websites when missing)

2. School Data Collection
   ├─ ComprehensiveSchoolCollector (primary)
   │  ├─ Firecrawl (scrape homepage)
   │  ├─ LLM Agent (extract description, acceptance rate)
   │  └─ Playwright (dynamic content)
   └─ College Scorecard API (financial data)

3. Program Discovery
   ├─ ProgramDiscoveryAgent
   │  ├─ Firecrawl crawl (program pages)
   │  ├─ LLM navigation (find listing pages)
   │  └─ Google search (fallback)
   └─ Extract program URLs

4. Program Data Collection
   ├─ ProgramCollectionAgent
   │  ├─ Firecrawl (structured extraction)
   │  ├─ LLM Agent (complex layouts)
   │  └─ Playwright (JavaScript content)
   └─ Validate & Save

5. Data Processing
   ├─ DataValidator (schema + business logic)
   ├─ DataQualityTracker (metrics)
   └─ Database storage
```

## Integration Points

### 1. With Existing Data Ingestion Service

The new components work alongside your existing `DataIngestionService`:

```python
# Existing code still works
from src.services.data_ingestion import DataIngestionService

service = DataIngestionService(db)
service.ingest_institution(institution_seed)  # Still works
service.ingest_program(program_seed, institution_id)  # Still works

# New: Enhanced collection
from src.scrapers.schools.comprehensive_collector import ComprehensiveSchoolCollector

collector = ComprehensiveSchoolCollector()
school_data = await collector.collect_school_data("MIT", "https://mit.edu")
# Then use service.ingest_institution() with enriched data
```

### 2. With Existing Worker Jobs

New Celery tasks complement existing ones:

```python
# Existing tasks still work
from src.workers.scraper_worker import scrape_institution_programs_task

# New comprehensive tasks
from src.workers.scraper_worker import (
    collect_school_comprehensive_task,
    discover_programs_task,
    collect_program_comprehensive_task
)

# Use them together
collect_school_comprehensive_task.delay(institution_id)
discover_programs_task.delay(institution_id)
```

### 3. With Existing Models

All new components use your existing models:

```python
from src.models.institution import Institution
from src.models.program import Program

# New collectors work with existing models
institution = db.query(Institution).first()
program_seed = await agent.collect_program_data(url, institution)
```

### 4. With Existing Validation

Enhanced validator extends existing validation:

```python
# Existing validation still works
from src.services.data_validator import validate_institution, validate_program

# New: Enhanced validation with completeness scoring
from src.services.data_validator import (
    calculate_completeness_score_institution,
    calculate_completeness_score_program,
    detect_duplicates
)

score = calculate_completeness_score_institution(seed)
deduplicated = detect_duplicates(schools)
```

## Migration Path

### Option 1: Gradual Adoption (Recommended)

1. **Keep existing scripts working** - They still work as before
2. **Test new system** - Run `quick_start_data_collection.py` first
3. **Use for new schools** - Use comprehensive collection for new schools
4. **Enhance existing** - Gradually enrich existing schools with comprehensive data

### Option 2: Full Migration

1. **Backup database** - Always backup before major changes
2. **Run comprehensive collection** - Collect data for all schools
3. **Update existing records** - Merge new data with existing
4. **Verify quality** - Check data quality metrics

## Usage Patterns

### Pattern 1: Quick Collection (New Schools)

```python
# Use when adding new schools
from src.scrapers.schools.multi_source_fetcher import MultiSourceFetcher
from src.scrapers.schools.comprehensive_collector import ComprehensiveSchoolCollector

fetcher = MultiSourceFetcher()
schools = await fetcher.fetch_all_schools(limit=10)

collector = ComprehensiveSchoolCollector()
for school in schools:
    data = await collector.collect_school_data(school.name, school.website_url)
    # Save to database
```

### Pattern 2: Program Discovery (Existing Schools)

```python
# Use when you have schools but need programs
from src.scrapers.agents.program_discovery_agent import ProgramDiscoveryAgent
from src.scrapers.agents.program_collection_agent import ProgramCollectionAgent

discovery = ProgramDiscoveryAgent()
program_urls = await discovery.discover_programs("MIT", "https://mit.edu")

collection = ProgramCollectionAgent()
for url in program_urls:
    program = await collection.collect_program_data(url, institution)
    # Save to database
```

### Pattern 3: Background Jobs (Large Batches)

```python
# Use for large-scale collection
from src.workers.scraper_worker import (
    collect_school_comprehensive_task,
    discover_programs_task
)

# Queue jobs
for institution in institutions:
    collect_school_comprehensive_task.delay(str(institution.id))
    discover_programs_task.delay(str(institution.id))
```

### Pattern 4: Batch Script (Easiest)

```bash
# Simplest way - handles everything
python -m scripts.comprehensive_data_collection --max-schools 50
```

## Data Flow Example

Here's what happens when you run the batch script:

```
1. MultiSourceFetcher
   └─> Fetches 50 schools from:
       - IPEDS (US schools)
       - Top schools lists
       - Rankings (QS, THE, etc.)
   └─> Deduplicates and ranks

2. For each school:
   a. ComprehensiveSchoolCollector
      └─> Tries Firecrawl (scrape homepage)
      └─> Falls back to LLM agent (extract description)
      └─> Uses Playwright (if dynamic content)
      └─> Enriches with College Scorecard
   
   b. ProgramDiscoveryAgent
      └─> Tries Firecrawl crawl (program pages)
      └─> Uses LLM to find listing page
      └─> Falls back to Google search
      └─> Extracts program URLs
   
   c. For each program URL:
      ProgramCollectionAgent
      └─> Tries Firecrawl (structured extraction)
      └─> Falls back to LLM agent (complex layouts)
      └─> Uses Playwright (JavaScript content)
      └─> Validates data
      └─> Saves to database

3. Data Quality Tracking
   └─> Records success rates
   └─> Calculates completeness scores
   └─> Tracks validation failures
   └─> Reports metrics
```

## Configuration

All components respect your existing configuration:

```python
# src/config.py
settings.firecrawl_api_key  # Used by FirecrawlScraper
settings.groq_api_key       # Used by LLM agents
settings.openai_api_key     # Alternative LLM provider
settings.enable_llm_extraction  # Toggle LLM features
settings.scraper_delay_seconds   # Rate limiting
```

New configuration options:
```python
settings.google_search_enabled
settings.playwright_browser
settings.playwright_timeout
settings.agent_max_steps
settings.agent_retry_attempts
```

## Error Handling

The system is designed to be resilient:

1. **Automatic Fallbacks**: If Firecrawl fails → LLM agent → Playwright
2. **Graceful Degradation**: Missing data is logged but doesn't stop collection
3. **Retry Logic**: Worker jobs retry with exponential backoff
4. **Error Tracking**: All errors logged to data quality tracker

## Performance Considerations

- **Firecrawl**: Fastest, use for bulk scraping
- **LLM Agents**: Slower but handles complex layouts
- **Playwright**: Slowest but necessary for dynamic content
- **Batch Processing**: Use Celery for large batches
- **Rate Limiting**: Built-in delays prevent blocking

## Next Steps

1. **Test**: Run `quick_start_data_collection.py`
2. **Small Batch**: Collect 10 schools
3. **Review**: Check data quality metrics
4. **Scale**: Increase to larger batches
5. **Automate**: Set up scheduled jobs

## Support

- Check logs: `guidr-backend/logs/`
- Review quality metrics in script output
- See [COMPREHENSIVE_DATA_COLLECTION_GUIDE.md](COMPREHENSIVE_DATA_COLLECTION_GUIDE.md) for details

