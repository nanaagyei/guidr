"""Multi-source school fetcher that aggregates schools from multiple sources."""
from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from src.scrapers.base import InstitutionSeed
from src.scrapers.schools.ipeds import IPEDSScraper
from src.scrapers.schools.scorecard import CollegeScorecardClient
from src.scrapers.schools.top_schools import TopSchoolsFetcher
from src.scrapers.schools.firecrawl_scraper import FirecrawlScraper

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Normalize school name for matching."""
    import re
    # Remove common suffixes and normalize
    normalized = name.lower()
    normalized = re.sub(r"\s*\(.*?\)", "", normalized)  # Remove parentheticals
    normalized = re.sub(r"university of", "u", normalized)
    normalized = re.sub(r"the\s+", "", normalized)
    normalized = re.sub(r"[^a-z0-9]", "", normalized)
    return normalized


def _similarity_score(name1: str, name2: str) -> float:
    """Calculate similarity between two school names."""
    norm1 = _normalize_name(name1)
    norm2 = _normalize_name(name2)
    return SequenceMatcher(None, norm1, norm2).ratio()


class MultiSourceFetcher:
    """Aggregates schools from multiple sources and deduplicates."""
    
    def __init__(self):
        self.ipeds_scraper = IPEDSScraper()
        self.top_schools_fetcher = TopSchoolsFetcher()
        self.firecrawl_scraper = FirecrawlScraper()
        self.scorecard_client = CollegeScorecardClient()
    
    async def fetch_all_schools(self, limit: int = 500) -> List[InstitutionSeed]:
        """
        Aggregate schools from all sources, deduplicate, and rank.
        
        Args:
            limit: Maximum number of schools to return
            
        Returns:
            List of deduplicated InstitutionSeed objects
        """
        all_schools: List[InstitutionSeed] = []
        
        # 1. Get curated top schools (highest priority)
        logger.info("Fetching curated top schools...")
        curated = self.firecrawl_scraper.get_curated_institutions(limit=200)
        all_schools.extend(curated)
        logger.info(f"Added {len(curated)} curated schools")
        
        # 2. Get top schools from rankings
        logger.info("Fetching top schools from rankings...")
        top_schools_data = self.top_schools_fetcher.fetch_all_top_schools()
        for school_data in top_schools_data[:300]:
            # Convert TopSchoolData to InstitutionSeed
            seed = InstitutionSeed(
                name=school_data.name,
                country=school_data.country,
                city=school_data.city,
                website_url=school_data.website_url,
                data_source="top_schools_rankings",
            )
            all_schools.append(seed)
        logger.info(f"Added {len(top_schools_data)} top ranked schools")
        
        # 3. Get IPEDS schools (US only, filter for graduate programs)
        logger.info("Fetching IPEDS schools...")
        try:
            ipeds_schools = self.ipeds_scraper.fetch_directory_data(year="2022", limit=300)
            all_schools.extend(ipeds_schools)
            logger.info(f"Added {len(ipeds_schools)} IPEDS schools")
        except Exception as e:
            logger.warning(f"Failed to fetch IPEDS data: {e}")
        
        # 4. Deduplicate
        logger.info("Deduplicating schools...")
        deduplicated = self.deduplicate_schools(all_schools)
        
        # 5. Enrich with rankings
        logger.info("Enriching with rankings...")
        enriched = await self.enrich_with_rankings(deduplicated)
        
        # 6. Sort by priority (curated > top ranked > IPEDS)
        enriched.sort(key=lambda s: (
            0 if s.data_source == "curated_top_schools" else
            1 if s.data_source == "top_schools_rankings" else
            2
        ))
        
        return enriched[:limit]
    
    def deduplicate_schools(self, schools: List[InstitutionSeed]) -> List[InstitutionSeed]:
        """
        Merge duplicate schools using fuzzy matching.
        
        Args:
            schools: List of schools to deduplicate
            
        Returns:
            Deduplicated list with merged data
        """
        if not schools:
            return []
        
        # Group by normalized name
        seen: Dict[str, InstitutionSeed] = {}
        
        for school in schools:
            key = _normalize_name(school.name)
            
            if key in seen:
                # Merge with existing school
                existing = seen[key]
                # Prefer non-null values
                if not existing.short_name and school.short_name:
                    existing.short_name = school.short_name
                if not existing.website_url and school.website_url:
                    existing.website_url = school.website_url
                if not existing.city and school.city:
                    existing.city = school.city
                if not existing.state_or_province and school.state_or_province:
                    existing.state_or_province = school.state_or_province
                if not existing.country and school.country:
                    existing.country = school.country
                # Keep highest priority data source
                if school.data_source == "curated_top_schools":
                    existing.data_source = school.data_source
            else:
                seen[key] = school
        
        # Also check for similar names (fuzzy match)
        result = list(seen.values())
        final_result: List[InstitutionSeed] = []
        processed = set()
        
        for i, school1 in enumerate(result):
            if i in processed:
                continue
            
            # Find similar schools
            similar_group = [school1]
            for j, school2 in enumerate(result[i+1:], start=i+1):
                if j in processed:
                    continue
                
                similarity = _similarity_score(school1.name, school2.name)
                if similarity > 0.85:  # 85% similarity threshold
                    similar_group.append(school2)
                    processed.add(j)
            
            # Merge similar schools
            if len(similar_group) > 1:
                merged = self._merge_similar_schools(similar_group)
                final_result.append(merged)
            else:
                final_result.append(school1)
            
            processed.add(i)
        
        logger.info(f"Deduplicated {len(schools)} schools to {len(final_result)} unique schools")
        return final_result
    
    def _merge_similar_schools(self, schools: List[InstitutionSeed]) -> InstitutionSeed:
        """Merge a group of similar schools into one."""
        # Use the first school as base
        merged = schools[0]
        
        # Merge all non-null fields
        for school in schools[1:]:
            if not merged.short_name and school.short_name:
                merged.short_name = school.short_name
            if not merged.website_url and school.website_url:
                merged.website_url = school.website_url
            if not merged.city and school.city:
                merged.city = school.city
            if not merged.state_or_province and school.state_or_province:
                merged.state_or_province = school.state_or_province
            if not merged.country and school.country:
                merged.country = school.country
            if not merged.institution_type and school.institution_type:
                merged.institution_type = school.institution_type
            if not merged.public_private and school.public_private:
                merged.public_private = school.public_private
            # Prefer curated data source
            if school.data_source == "curated_top_schools":
                merged.data_source = school.data_source
        
        return merged
    
    async def enrich_with_rankings(self, schools: List[InstitutionSeed]) -> List[InstitutionSeed]:
        """
        Add ranking data from multiple sources.
        
        Args:
            schools: List of schools to enrich
            
        Returns:
            Enriched schools with ranking data
        """
        # Get top schools data which includes rankings
        top_schools_data = self.top_schools_fetcher.fetch_all_top_schools()
        
        # Create lookup by name
        rankings_lookup: Dict[str, Dict] = {}
        for school_data in top_schools_data:
            key = _normalize_name(school_data.name)
            rankings_lookup[key] = {
                "qs_rank": school_data.qs_rank,
                "the_rank": school_data.the_rank,
                "arwu_rank": school_data.arwu_rank,
                "usnews_rank": school_data.usnews_rank,
            }
        
        # Enrich schools with rankings
        for school in schools:
            key = _normalize_name(school.name)
            if key in rankings_lookup:
                # Note: InstitutionSeed doesn't have ranking fields,
                # but we can add them if needed in the future
                # For now, we'll just log that we found rankings
                pass
        
        return schools

