"""Meilisearch integration helpers."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from meilisearch import Client
from meilisearch.errors import MeilisearchError

from src.config import settings

logger = logging.getLogger(__name__)

INSTITUTIONS_INDEX = "institutions"
PROGRAMS_INDEX = "programs"
FUNDING_INDEX = "funding"


class SearchService:
    def __init__(self) -> None:
        self._client: Optional[Client] = None

    @property
    def enabled(self) -> bool:
        return bool(settings.meilisearch_host)

    def _get_client(self) -> Client:
        if not self.enabled:
            raise RuntimeError("Meilisearch not configured.")
        if self._client is None:
            self._client = Client(settings.meilisearch_host, settings.meilisearch_master_key)
        return self._client

    def ensure_indexes(self) -> None:
        if not self.enabled:
            return
        client = self._get_client()
        for base in (INSTITUTIONS_INDEX, PROGRAMS_INDEX, FUNDING_INDEX):
            try:
                task = client.create_index(self._index_name(base), {"primaryKey": "id"})
                client.wait_for_task(task.task_uid, timeout_in_ms=5000)
            except MeilisearchError:
                continue

        # Configure filterable/sortable attributes per index
        index_settings = {
            INSTITUTIONS_INDEX: {
                "filterable": [
                    "country", "state_or_province", "institution_type",
                    "public_private",
                ],
                "sortable": ["name", "data_completeness_score"],
            },
            PROGRAMS_INDEX: {
                "filterable": [
                    "degree_level", "field_of_study", "institution_name",
                    "institution_country",
                ],
                "sortable": [
                    "name", "tuition_estimate_per_year",
                    "application_deadline_primary",
                ],
            },
            FUNDING_INDEX: {
                "filterable": [
                    "funding_type", "covers_tuition", "covers_stipend",
                    "is_need_based", "is_merit_based", "institution_country",
                    "institution_id",
                ],
                "sortable": ["name", "amount_min", "amount_max", "deadline"],
            },
        }
        for base, attrs in index_settings.items():
            try:
                idx = client.index(self._index_name(base))
                idx.update_filterable_attributes(attrs["filterable"])
                idx.update_sortable_attributes(attrs["sortable"])
            except MeilisearchError as exc:
                logger.warning("Failed to configure %s index attributes: %s", base, exc)

    def index_institution(self, payload: Dict) -> None:
        self._index_documents(self._index_name(INSTITUTIONS_INDEX), [payload])

    def index_program(self, payload: Dict) -> None:
        self._index_documents(self._index_name(PROGRAMS_INDEX), [payload])

    def batch_index_institutions(self, payloads: List[Dict]) -> None:
        self._index_documents(self._index_name(INSTITUTIONS_INDEX), payloads)

    def batch_index_programs(self, payloads: List[Dict]) -> None:
        self._index_documents(self._index_name(PROGRAMS_INDEX), payloads)

    def index_funding(self, payload: Dict) -> None:
        self._index_documents(self._index_name(FUNDING_INDEX), [payload])

    def batch_index_funding(self, payloads: List[Dict]) -> None:
        self._index_documents(self._index_name(FUNDING_INDEX), payloads)

    def delete_funding(self, item_id: str) -> None:
        self._delete_document(self._index_name(FUNDING_INDEX), item_id)

    def delete_institution(self, item_id: str) -> None:
        self._delete_document(self._index_name(INSTITUTIONS_INDEX), item_id)

    def delete_program(self, item_id: str) -> None:
        self._delete_document(self._index_name(PROGRAMS_INDEX), item_id)

    def search_institutions(self, query: str, filters: Optional[str] = None, limit: int = 20) -> Optional[Dict]:
        if not self.enabled:
            return None
        try:
            return (
                self._get_client()
                .index(self._index_name(INSTITUTIONS_INDEX))
                .search(query, {"limit": limit, "filter": filters})
            )
        except MeilisearchError as exc:  # pragma: no cover
            logger.warning("Meilisearch search failed: %s", exc)
            return None

    def search_programs(self, query: str, filters: Optional[str] = None, limit: int = 20, offset: int = 0) -> Optional[Dict]:
        if not self.enabled:
            return None
        try:
            return (
                self._get_client()
                .index(self._index_name(PROGRAMS_INDEX))
                .search(
                    query,
                    {
                        "limit": limit,
                        "offset": offset,
                        "filter": filters,
                    },
                )
            )
        except MeilisearchError as exc:  # pragma: no cover
            logger.warning("Meilisearch search failed: %s", exc)
            return None

    def search_funding(self, query: str, filters: Optional[str] = None, limit: int = 20, offset: int = 0) -> Optional[Dict]:
        if not self.enabled:
            return None
        try:
            return (
                self._get_client()
                .index(self._index_name(FUNDING_INDEX))
                .search(
                    query,
                    {
                        "limit": limit,
                        "offset": offset,
                        "filter": filters,
                    },
                )
            )
        except MeilisearchError as exc:  # pragma: no cover
            logger.warning("Meilisearch search failed: %s", exc)
            return None

    def serialize_institution(self, institution) -> Dict:
        return {
            "id": str(institution.id),
            "name": institution.name,
            "country": institution.country,
            "city": institution.city,
            "state_or_province": institution.state_or_province,
            "short_name": institution.short_name,
            "website_url": institution.website_url,
            "institution_type": institution.institution_type,
            "public_private": institution.public_private,
            "data_completeness_score": institution.data_completeness_score,
        }

    def serialize_program(self, program) -> Dict:
        return {
            "id": str(program.id),
            "name": program.name,
            "degree_level": program.degree_level,
            "field_of_study": program.field_of_study,
            "institution_name": program.institution.name if program.institution else None,
            "institution_country": program.institution.country if program.institution else None,
            "institution_city": program.institution.city if program.institution else None,
            "tuition_estimate_per_year": float(program.tuition_estimate_per_year) if program.tuition_estimate_per_year else None,
            "application_deadline_primary": program.application_deadline_primary.isoformat()
            if program.application_deadline_primary
            else None,
            "description": program.description,
        }

    def serialize_funding(self, funding) -> Dict:
        inst = funding.institution
        return {
            "id": str(funding.id),
            "name": funding.name,
            "funding_type": funding.funding_type,
            "amount_min": float(funding.amount_min) if funding.amount_min else None,
            "amount_max": float(funding.amount_max) if funding.amount_max else None,
            "amount_period": funding.amount_period,
            "deadline": funding.deadline.isoformat() if funding.deadline else None,
            "description": funding.description,
            "covers_tuition": funding.covers_tuition,
            "covers_stipend": funding.covers_stipend,
            "is_need_based": funding.is_need_based,
            "is_merit_based": funding.is_merit_based,
            "website_url": funding.website_url,
            "institution_id": str(funding.institution_id),
            "institution_name": inst.name if inst else None,
            "institution_country": inst.country if inst else None,
        }

    def _index_documents(self, index_name: str, payloads: List[Dict]) -> None:
        if not self.enabled or not payloads:
            return
        try:
            self._get_client().index(index_name).add_documents(payloads)
        except MeilisearchError as exc:  # pragma: no cover
            logger.warning("Failed to index documents: %s", exc)

    def _delete_document(self, index_name: str, item_id: str) -> None:
        if not self.enabled:
            return
        try:
            self._get_client().index(index_name).delete_document(item_id)
        except MeilisearchError as exc:  # pragma: no cover
            logger.warning("Failed to delete document: %s", exc)

    def _index_name(self, base: str) -> str:
        return f"{settings.meilisearch_index_prefix}_{base}"

    def clear_all_indexes(self) -> None:
        """Delete all documents from all indexes."""
        if not self.enabled:
            return
        client = self._get_client()
        for base in (INSTITUTIONS_INDEX, PROGRAMS_INDEX, FUNDING_INDEX):
            try:
                index = client.index(self._index_name(base))
                task = index.delete_all_documents()
                client.wait_for_task(task.task_uid, timeout_in_ms=10000)
                logger.info("Cleared index: %s", self._index_name(base))
            except MeilisearchError as exc:
                logger.warning("Failed to clear index %s: %s", base, exc)


search_service = SearchService()
