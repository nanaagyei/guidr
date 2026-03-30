"""Quick start script for testing the comprehensive data collection system."""
import asyncio
import logging
from src.scrapers.schools.multi_source_fetcher import MultiSourceFetcher
from src.scrapers.schools.comprehensive_collector import ComprehensiveSchoolCollector
from src.scrapers.agents.program_discovery_agent import ProgramDiscoveryAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def quick_test():
    """Quick test of the data collection system with 3 schools."""
    logger.info("=" * 60)
    logger.info("Quick Start: Testing Comprehensive Data Collection")
    logger.info("=" * 60)
    
    # Step 1: Fetch a few schools
    logger.info("\n1. Fetching top 3 schools...")
    fetcher = MultiSourceFetcher()
    schools = await fetcher.fetch_all_schools(limit=3)
    
    for i, school in enumerate(schools, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"School {i}: {school.name}")
        logger.info(f"  Country: {school.country}")
        logger.info(f"  Website: {school.website_url}")
        
        if not school.website_url:
            logger.warning("  No website URL - skipping collection")
            continue
        
        # Step 2: Collect school data
        logger.info("\n2. Collecting comprehensive school data...")
        collector = ComprehensiveSchoolCollector()
        try:
            school_data = await collector.collect_school_data(
                school.name,
                school.website_url
            )
            
            logger.info(f"  Description: {school_data.get('description', 'N/A')[:100]}...")
            logger.info(f"  Acceptance Rate: {school_data.get('acceptance_rate', 'N/A')}")
            logger.info(f"  Tuition: {school_data.get('tuition', {})}")
            
        except Exception as e:
            logger.error(f"  Error collecting school data: {e}")
        finally:
            await collector.close()
        
        # Step 3: Discover programs
        logger.info("\n3. Discovering programs...")
        discovery = ProgramDiscoveryAgent()
        try:
            program_urls = await discovery.discover_programs(
                school.name,
                school.website_url
            )
            logger.info(f"  Found {len(program_urls)} programs")
            if program_urls:
                logger.info(f"  Sample programs:")
                for url in program_urls[:3]:
                    logger.info(f"    - {url}")
        except Exception as e:
            logger.error(f"  Error discovering programs: {e}")
        finally:
            await discovery.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("Quick test complete!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Review the output above")
    logger.info("2. Run full collection: python -m scripts.comprehensive_data_collection --max-schools 10")
    logger.info("3. Check the guide: docs/COMPREHENSIVE_DATA_COLLECTION_GUIDE.md")


if __name__ == "__main__":
    asyncio.run(quick_test())

