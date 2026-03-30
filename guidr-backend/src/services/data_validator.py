"""Validation helpers for ingestion pipelines."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse

# Note: re is used in detect_duplicates function

from src.scrapers.base import InstitutionSeed, ProgramSeed


class ValidationError(Exception):
    """Raised when incoming data fails basic validation."""


def ensure_required_fields(seed, required_fields: Iterable[str]) -> None:
    missing: List[str] = [
        field for field in required_fields if not getattr(seed, field, None)
    ]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")


def validate_institution(seed: InstitutionSeed) -> InstitutionSeed:
    """Enhanced institution validation with business logic."""
    ensure_required_fields(seed, ["name", "country"])
    
    # Validate website URL format
    if seed.website_url:
        if not _is_valid_url(seed.website_url):
            raise ValidationError(f"Invalid website URL: {seed.website_url}")
    
    # Validate country/state consistency
    if seed.country == "USA" and not seed.state_or_province:
        # Warning but not error - some US schools might not have state
        pass
    
    return seed


def validate_program(seed: ProgramSeed) -> ProgramSeed:
    """Enhanced program validation with business logic."""
    ensure_required_fields(seed, ["institution_name", "name", "degree_level"])
    
    # Validate program name - reject common error/page titles
    invalid_names = [
        "unknown program",
        "404",
        "404 not found",
        "page not found",
        "not found",
        "error 404",
        "error",
        "home",
        "index",
        "catalog",
        "programs a-z",
        "programs",
        "graduate catalog",
        "graduate programs",
        "degrees",
        "graduate admissions",
        "admissions",
        "admission",
        "apply",
        "application",
    ]
    
    name_lower = (seed.name or "").lower().strip()
    if not name_lower or len(name_lower) < 3:
        raise ValidationError(f"Program name too short or empty: {seed.name}")
    
    # Check if name is an invalid error/page title
    if any(invalid in name_lower for invalid in invalid_names):
        raise ValidationError(f"Invalid program name (appears to be error/page title): {seed.name}")
    
    # Reject names that are clearly page titles (contain common separators)
    if "|" in seed.name or " - " in seed.name or seed.name.startswith("Home"):
        raise ValidationError(f"Invalid program name (appears to be page title): {seed.name}")
    
    # Reject names that look like headings (e.g., "the New Era of...")
    words = name_lower.split()
    if len(words) >= 4 and words[0] == "the" and "of" in words:
        # This pattern usually indicates a heading, not a program name
        raise ValidationError(f"Invalid program name (appears to be page heading): {seed.name}")
    
    # Reject taglines and marketing phrases
    tagline_patterns = [
        "world changers",
        "future makers",
        "we can imagine",
        "be the light",
        "the new era",
        "experience",
        "discover",
        "explore",
        "welcome",
    ]
    if any(tagline in name_lower for tagline in tagline_patterns):
        raise ValidationError(f"Invalid program name (appears to be tagline/marketing phrase): {seed.name}")
    
    # Reject if it ends with a period (likely a sentence/tagline)
    if seed.name.endswith("."):
        raise ValidationError(f"Invalid program name (appears to be a sentence): {seed.name}")
    
    # Reject single generic words
    generic_words = ["departments", "programs", "degrees", "catalog", "admissions"]
    if name_lower in generic_words:
        raise ValidationError(f"Invalid program name (generic word): {seed.name}")
    
    # Validate degree level
    valid_degree_levels = ["masters", "phd", "professional", "certificate"]
    if seed.degree_level and seed.degree_level not in valid_degree_levels:
        raise ValidationError(f"Invalid degree_level: {seed.degree_level}")
    
    # Validate deadline dates (must be in future for upcoming terms)
    if seed.application_deadline_primary:
        deadline = _parse_date(seed.application_deadline_primary)
        if deadline:
            # Allow deadlines up to 2 years in the future (for planning)
            max_future_date = date.today().replace(year=date.today().year + 2)
            if deadline > max_future_date:
                raise ValidationError(f"Deadline too far in future: {deadline}")
            # Past deadlines are OK (historical data)
    
    # Validate tuition >= 0
    if seed.tuition_estimate_per_year is not None and seed.tuition_estimate_per_year < 0:
        raise ValidationError(f"Invalid tuition (negative): {seed.tuition_estimate_per_year}")
    
    # Validate website URL
    if seed.website_url:
        if not _is_valid_url(seed.website_url):
            raise ValidationError(f"Invalid website URL: {seed.website_url}")
    
    return seed


def _is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme in ["http", "https"], result.netloc])
    except Exception:
        return False


def _parse_date(date_str: str) -> Optional[date]:
    """Parse date string to date object."""
    if not date_str:
        return None
    
    # Common date formats
    formats = [
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    
    return None


def calculate_completeness_score_institution(seed: InstitutionSeed) -> int:
    """
    Calculate data completeness score for institution (0-100).
    
    Required fields (40%): name, country, website
    Optional fields (60%): city, state, rank, type, public_private
    """
    required_fields = ["name", "country", "website_url"]
    optional_fields = ["city", "state_or_province", "institution_type", "public_private"]
    
    required_score = sum(1 for field in required_fields if getattr(seed, field, None)) / len(required_fields) * 40
    optional_score = sum(1 for field in optional_fields if getattr(seed, field, None)) / len(optional_fields) * 60
    
    return int(required_score + optional_score)


def calculate_completeness_score_program(seed: ProgramSeed) -> int:
    """
    Calculate data completeness score for program (0-100).
    
    Required (30%): name, degree_level, institution_name
    Important (50%): description, deadline, tuition
    Optional (20%): field_of_study, website_url, application_fee
    """
    required_fields = ["name", "degree_level", "institution_name"]
    important_fields = ["description", "application_deadline_primary", "tuition_estimate_per_year"]
    optional_fields = ["field_of_study", "website_url", "application_fee"]
    
    required_score = sum(1 for field in required_fields if getattr(seed, field, None)) / len(required_fields) * 30
    important_score = sum(1 for field in important_fields if getattr(seed, field, None)) / len(important_fields) * 50
    optional_score = sum(1 for field in optional_fields if getattr(seed, field, None)) / len(optional_fields) * 20
    
    return int(required_score + important_score + optional_score)


def detect_duplicates(
    seeds: List[InstitutionSeed],
    similarity_threshold: float = 0.85
) -> List[InstitutionSeed]:
    """
    Detect and merge duplicate institutions using fuzzy matching.
    
    Args:
        seeds: List of institution seeds
        similarity_threshold: Similarity score threshold (0-1)
        
    Returns:
        Deduplicated list
    """
    from difflib import SequenceMatcher
    
    def normalize_name(name: str) -> str:
        name = name.lower()
        name = re.sub(r"\s*\(.*?\)", "", name)
        name = re.sub(r"university of", "u", name)
        name = re.sub(r"[^a-z0-9]", "", name)
        return name
    
    def similarity(name1: str, name2: str) -> float:
        norm1 = normalize_name(name1)
        norm2 = normalize_name(name2)
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    seen = set()
    unique_seeds = []
    
    for seed in seeds:
        normalized = normalize_name(seed.name)
        
        # Check if similar seed already exists
        found_duplicate = False
        for i, existing in enumerate(unique_seeds):
            if similarity(seed.name, existing.name) >= similarity_threshold:
                # Merge with existing
                unique_seeds[i] = _merge_institutions(existing, seed)
                found_duplicate = True
                break
        
        if not found_duplicate:
            unique_seeds.append(seed)
    
    return unique_seeds


def _merge_institutions(seed1: InstitutionSeed, seed2: InstitutionSeed) -> InstitutionSeed:
    """Merge two institution seeds, preferring non-null values."""
    # Use seed1 as base
    merged = InstitutionSeed(
        name=seed1.name,
        country=seed1.country or seed2.country,
        short_name=seed1.short_name or seed2.short_name,
        state_or_province=seed1.state_or_province or seed2.state_or_province,
        city=seed1.city or seed2.city,
        website_url=seed1.website_url or seed2.website_url,
        institution_type=seed1.institution_type or seed2.institution_type,
        public_private=seed1.public_private or seed2.public_private,
        ipeds_unit_id=seed1.ipeds_unit_id or seed2.ipeds_unit_id,
        scorecard_school_id=seed1.scorecard_school_id or seed2.scorecard_school_id,
        data_source=seed1.data_source if seed1.data_source == "curated_top_schools" else seed2.data_source,
    )
    return merged

