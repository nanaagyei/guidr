"""High-level ingestion orchestration for Phase 1."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.models.institution import Institution
from src.models.program import Program
from src.scrapers.base import InstitutionSeed
from src.scrapers.schools import CollegeScorecardClient, IPEDSScraper
from src.scrapers.schools.firecrawl_scraper import FirecrawlScraper, get_top_graduate_schools
from src.services import data_validator
from src.services.embedding_service import embedding_service
from src.services.search_service import search_service
from src.utils.data_completeness import calculate_institution_completeness

logger = logging.getLogger(__name__)


class DataIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest_ipeds(self, *, year: str = "2022", limit: Optional[int] = None) -> Dict[str, int]:
        with IPEDSScraper() as scraper:
            seeds = scraper.fetch_directory_data(year=year, limit=limit)
        inserted = 0
        updated = 0
        search_payloads: List[Dict] = []
        for seed in seeds:
            try:
                data_validator.validate_institution(seed)
            except data_validator.ValidationError as exc:
                logger.debug("Skipping institution %s: %s", seed.name, exc)
                continue
            institution, created = self._upsert_institution(seed)
            if created:
                inserted += 1
            else:
                updated += 1
            payload = search_service.serialize_institution(institution)
            search_payloads.append(payload)
        self.db.commit()
        search_service.batch_index_institutions(search_payloads)
        logger.info("IPEDS ingestion complete. inserted=%s updated=%s", inserted, updated)
        return {"inserted": inserted, "updated": updated}

    def enrich_with_scorecard(self, batch_size: int = 100) -> Dict[str, int]:
        query = (
            self.db.query(Institution)
            .filter(Institution.ipeds_unit_id.isnot(None))
            .order_by(Institution.updated_at.desc())
        )
        institutions = query.all()
        unit_ids = [inst.ipeds_unit_id for inst in institutions if inst.ipeds_unit_id]
        client = CollegeScorecardClient()
        metrics_map = client.fetch_financials(unit_ids)
        updated = 0
        for institution in institutions:
            metrics = metrics_map.get(institution.ipeds_unit_id)
            if not metrics:
                continue
            institution.average_cost = metrics.average_cost
            institution.in_state_tuition = metrics.in_state_tuition
            institution.out_of_state_tuition = metrics.out_of_state_tuition
            institution.graduation_rate = metrics.graduation_rate
            institution.median_earnings = metrics.median_earnings
            institution.updated_at = datetime.utcnow()
            institution.data_completeness_score = calculate_institution_completeness(
                {
                    "name": institution.name,
                    "country": institution.country,
                    "website_url": institution.website_url,
                    "city": institution.city,
                    "state_or_province": institution.state_or_province,
                    "institution_type": institution.institution_type,
                    "public_private": institution.public_private,
                }
            )
            embedding = embedding_service.embed_institution(institution)
            if embedding:
                institution.embedding = embedding
            updated += 1
        self.db.commit()
        return {"enriched": updated}

    def reindex_search(self) -> Dict[str, int]:
        from src.models.funding_opportunity import FundingOpportunity

        institutions = self.db.query(Institution).all()
        payloads = [search_service.serialize_institution(inst) for inst in institutions]
        search_service.batch_index_institutions(payloads)

        programs = self.db.query(Program).all()
        program_payloads = [search_service.serialize_program(prog) for prog in programs]
        search_service.batch_index_programs(program_payloads)

        funding = self.db.query(FundingOpportunity).all()
        funding_payloads = [search_service.serialize_funding(f) for f in funding]
        search_service.batch_index_funding(funding_payloads)

        return {
            "institutions": len(payloads),
            "programs": len(program_payloads),
            "funding": len(funding_payloads),
        }

    def _upsert_institution(self, seed: InstitutionSeed) -> Tuple[Institution, bool]:
        existing = None
        if seed.scorecard_school_id:
            existing = (
                self.db.query(Institution)
                .filter(Institution.scorecard_school_id == seed.scorecard_school_id)
                .first()
            )
        if existing is None and seed.ipeds_unit_id:
            existing = (
                self.db.query(Institution)
                .filter(Institution.ipeds_unit_id == seed.ipeds_unit_id)
                .first()
            )
        if existing is None:
            existing = (
                self.db.query(Institution)
                .filter(Institution.name.ilike(seed.name))
                .first()
            )
        if existing:
            self._apply_seed(existing, seed)
            created = False
        else:
            existing = Institution()
            self._apply_seed(existing, seed)
            self.db.add(existing)
            self.db.flush()
            created = True
        embedding = embedding_service.embed_institution(existing)
        if embedding:
            existing.embedding = embedding
        existing.data_completeness_score = calculate_institution_completeness(
            {
                "name": existing.name,
                "country": existing.country,
                "website_url": existing.website_url,
                "city": existing.city,
                "state_or_province": existing.state_or_province,
                "institution_type": existing.institution_type,
                "public_private": existing.public_private,
            }
        )
        return existing, created

    def _apply_seed(self, institution: Institution, seed: InstitutionSeed) -> None:
        institution.name = seed.name
        institution.short_name = seed.short_name
        institution.country = seed.country
        institution.state_or_province = seed.state_or_province
        institution.city = seed.city
        institution.website_url = seed.website_url
        institution.institution_type = seed.institution_type
        institution.public_private = seed.public_private
        institution.ipeds_unit_id = seed.ipeds_unit_id
        institution.scorecard_school_id = seed.scorecard_school_id
        institution.data_source = seed.data_source or "ipeds"

    def load_graduate_schools_from_scorecard(
        self,
        state: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, int]:
        """Load graduate schools from College Scorecard API.

        Fetches all US schools offering graduate degrees, creates/updates
        Institution records. Optionally filter by state or limit count.

        Args:
            state: Optional state filter (e.g., 'CA', 'NY').
            limit: Optional max schools to load (for testing).

        Returns:
            Dict with inserted, updated, errors counts.
        """
        from src.scrapers.schools.scorecard import CollegeScorecardClient

        client = CollegeScorecardClient()
        inserted = 0
        updated = 0
        errors = 0
        search_payloads: List[Dict] = []

        for seed in client.get_graduate_schools(state=state):
            if limit and (inserted + updated) >= limit:
                break
            try:
                data_validator.validate_institution(seed)
            except data_validator.ValidationError as exc:
                logger.debug("Skip institution %s: %s", seed.name, exc)
                errors += 1
                continue
            try:
                institution, created = self._upsert_institution(seed)
                if created:
                    inserted += 1
                else:
                    updated += 1
                payload = search_service.serialize_institution(institution)
                search_payloads.append(payload)
            except Exception as exc:
                logger.error("Error upserting %s: %s", seed.name, exc)
                errors += 1

        self.db.commit()
        if search_payloads:
            search_service.batch_index_institutions(search_payloads)

        # Store audit record in data lake
        try:
            from src.pipeline.clients.storage_client import DataLakeStorageClient
            storage = DataLakeStorageClient()
            audit = {
                "source": "college_scorecard",
                "inserted": inserted,
                "updated": updated,
                "errors": errors,
                "state_filter": state,
                "limit": limit,
            }
            storage.store_json("audit", "scorecard_load", "load_summary.json", audit)
        except Exception as exc:
            logger.debug("Could not store scorecard load audit: %s", exc)

        logger.info(
            "Scorecard load complete. inserted=%s updated=%s errors=%s",
            inserted, updated, errors,
        )
        return {"inserted": inserted, "updated": updated, "errors": errors}

    def ingest_top_graduate_schools(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Ingest curated list of top graduate schools.

        This uses a built-in curated list of top universities known
        for their graduate programs - no external API required.
        """
        seeds = get_top_graduate_schools(limit=limit)
        inserted = 0
        updated = 0
        search_payloads: List[Dict] = []

        for seed in seeds:
            try:
                data_validator.validate_institution(seed)
            except data_validator.ValidationError as exc:
                logger.debug("Skipping institution %s: %s", seed.name, exc)
                continue

            institution, created = self._upsert_institution(seed)
            if created:
                inserted += 1
            else:
                updated += 1

            payload = search_service.serialize_institution(institution)
            search_payloads.append(payload)

        self.db.commit()
        search_service.batch_index_institutions(search_payloads)
        logger.info("Top graduate schools ingestion complete. inserted=%s updated=%s", inserted, updated)
        return {"inserted": inserted, "updated": updated}

    def ingest_institution(self, seed: InstitutionSeed) -> Institution:
        """Public method to ingest a single institution from a seed."""
        try:
            data_validator.validate_institution(seed)
        except data_validator.ValidationError as exc:
            logger.warning("Validation failed for institution %s: %s", seed.name, exc)
            raise
        institution, created = self._upsert_institution(seed)
        if created:
            logger.info("Created institution: %s", institution.name)
        else:
            logger.info("Updated institution: %s", institution.name)
        return institution

    def ingest_program(self, seed, institution_id) -> Program:
        """Public method to ingest a single program from a seed."""
        from src.scrapers.base import ProgramSeed
        from uuid import UUID

        if not isinstance(seed, ProgramSeed):
            raise ValueError("seed must be a ProgramSeed instance")

        try:
            data_validator.validate_program(seed)
        except data_validator.ValidationError as exc:
            logger.warning("Validation failed for program %s: %s", seed.name, exc)
            raise

        # Ensure institution_id is a UUID
        if isinstance(institution_id, str):
            institution_uuid = UUID(institution_id)
        elif isinstance(institution_id, UUID):
            institution_uuid = institution_id
        else:
            institution_uuid = UUID(str(institution_id))

        institution = self.db.query(Institution).filter(
            Institution.id == institution_uuid
        ).first()

        if not institution:
            raise ValueError(f"Institution {institution_id} not found")

        # Check if program already exists - ensure we use the UUID properly
        existing = self.db.query(Program).filter(
            Program.institution_id == institution_uuid,
            Program.name == seed.name
        ).first()

        if existing:
            # Update existing
            existing.degree_level = seed.degree_level or existing.degree_level
            existing.field_of_study = seed.field_of_study or existing.field_of_study
            existing.description = seed.description or existing.description
            existing.website_url = seed.website_url or existing.website_url
            existing.application_deadline_primary = seed.application_deadline_primary or existing.application_deadline_primary
            existing.tuition_estimate_per_year = seed.tuition_estimate_per_year or existing.tuition_estimate_per_year
            existing.application_fee = seed.application_fee or existing.application_fee
            existing.program_features = seed.program_features or existing.program_features
            existing.data_source = seed.data_source or existing.data_source
            existing.updated_at = datetime.utcnow()
            return existing

        # Create new program - use institution_uuid to ensure consistency
        program = Program(
            institution_id=institution_uuid,
            name=seed.name,
            degree_level=seed.degree_level,
            field_of_study=seed.field_of_study,
            description=seed.description,
            website_url=seed.website_url,
            application_deadline_primary=seed.application_deadline_primary,
            tuition_estimate_per_year=seed.tuition_estimate_per_year,
            application_fee=seed.application_fee,
            program_features=seed.program_features,
            data_source=seed.data_source or "comprehensive_scraping",
        )
        self.db.add(program)
        self.db.flush()

        # Generate embedding
        embedding = embedding_service.embed_program(program)
        if embedding:
            program.embedding = embedding

        logger.info("Created program: %s for %s", program.name, institution.name)
        return program

    def scrape_programs_with_firecrawl(
        self,
        institution_id: str,
        programs_url: str,
        max_programs: int = 20
    ) -> Dict[str, int]:
        """Scrape graduate programs using Firecrawl API.

        Requires FIRECRAWL_API_KEY to be set.
        """
        import asyncio
        from uuid import UUID

        institution = self.db.query(Institution).filter(
            Institution.id == UUID(institution_id)
        ).first()

        if not institution:
            logger.warning("Institution %s not found", institution_id)
            return {"error": "Institution not found", "programs": 0}

        scraper = FirecrawlScraper()
        if not scraper.is_available():
            logger.warning("Firecrawl API not configured")
            return {"error": "Firecrawl not configured", "programs": 0}

        # Run async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            program_seeds = loop.run_until_complete(
                scraper.scrape_programs_for_school(
                    institution.name,
                    programs_url,
                    max_programs
                )
            )
        finally:
            loop.close()

        # Insert programs
        inserted = 0
        for seed in program_seeds:
            existing = self.db.query(Program).filter(
                Program.institution_id == institution.id,
                Program.name == seed.name
            ).first()

            if existing:
                continue

            program = Program(
                institution_id=institution.id,
                name=seed.name,
                degree_level=seed.degree_level,
                field_of_study=seed.field_of_study,
                description=seed.description,
                website_url=seed.website_url,
                data_source="firecrawl",
            )
            self.db.add(program)
            inserted += 1

        self.db.commit()
        logger.info("Scraped %d programs for %s", inserted, institution.name)
        return {"institution": institution.name, "programs": inserted}
