"""College Scorecard API client."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Generator, List, Optional

from src.scrapers.base import BaseFetcher, chunked
from src.scrapers.base import InstitutionSeed
from src.config import settings

logger = logging.getLogger(__name__)


SCORECARD_BASE_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
SCORECARD_FIELDS = [
    "id",
    "school.name",
    "location.city",
    "location.state",
    "latest.cost.avg_net_price.overall",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.completion.rate_suppressed",
    "latest.earnings.10_yrs_after_entry.median",
]

# Fields for bulk graduate school load
GRADUATE_SCHOOL_FIELDS = [
    "id",
    "school.name",
    "school.alias",
    "school.city",
    "school.state",
    "school.zip",
    "school.school_url",
    "location.city",
    "location.state",
    "school.region_id",
    "school.ownership",
    "school.degrees_awarded.highest",
    "latest.student.size",
    "latest.student.grad_students",
    "latest.admissions.admission_rate.overall",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.cost.avg_net_price.overall",
    "latest.earnings.10_yrs_after_entry.median",
]

OWNERSHIP_MAP = {1: "public", 2: "private", 3: "private"}
RATE_LIMIT_PER_HOUR = 1000


@dataclass
class ScorecardFinancials:
    unit_id: str
    average_cost: Optional[float]
    in_state_tuition: Optional[float]
    out_of_state_tuition: Optional[float]
    graduation_rate: Optional[float]
    median_earnings: Optional[float]


class CollegeScorecardClient(BaseFetcher):
    """Minimal wrapper for the College Scorecard REST API."""

    def __init__(self, *, api_key: Optional[str] = None, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.api_key = api_key or settings.college_scorecard_api_key

    def fetch_financials(self, unit_ids: List[str]) -> Dict[str, ScorecardFinancials]:
        if not unit_ids:
            return {}
        if not self.api_key:
            logger.warning("College Scorecard API key missing; skipping enrichment.")
            return {}
        results: Dict[str, ScorecardFinancials] = {}
        for batch in chunked(unit_ids, 100):
            params = self._build_params(batch)
            response = self._get_client().get(SCORECARD_BASE_URL, params=params)
            response.raise_for_status()
            payload = response.json()
            for row in payload.get("results", []):
                mapped = self._map_row(row)
                results[mapped.unit_id] = mapped
        return results

    def _build_params(self, unit_ids: List[str]) -> Dict[str, str]:
        return {
            "api_key": self.api_key,
            "per_page": str(len(unit_ids)),
            "fields": ",".join(SCORECARD_FIELDS),
            "id": ",".join(unit_ids),
        }

    def _map_row(self, row: dict) -> ScorecardFinancials:
        def _to_float(value: Optional[float]) -> Optional[float]:
            try:
                if value is None or value == "":
                    return None
                return float(value)
            except (ValueError, TypeError):
                return None

        return ScorecardFinancials(
            unit_id=str(row.get("id")),
            average_cost=_to_float(row.get("latest.cost.avg_net_price.overall")),
            in_state_tuition=_to_float(row.get("latest.cost.tuition.in_state")),
            out_of_state_tuition=_to_float(row.get("latest.cost.tuition.out_of_state")),
            graduation_rate=_to_float(row.get("latest.completion.rate_suppressed")),
            median_earnings=_to_float(row.get("latest.earnings.10_yrs_after_entry.median")),
        )

    def _check_rate_limit(self, request_count: int, hour_start: datetime) -> tuple[int, datetime]:
        """Enforce 1000 requests/hour. Returns (new_count, new_hour_start)."""
        now = datetime.utcnow()
        elapsed_hours = (now - hour_start).total_seconds() / 3600
        if elapsed_hours >= 1:
            return 0, now
        if request_count >= RATE_LIMIT_PER_HOUR:
            sleep_secs = 3600 - (now - hour_start).total_seconds()
            logger.warning("College Scorecard rate limit reached, sleeping %.0fs", sleep_secs)
            time.sleep(max(1, sleep_secs))
            return 0, datetime.utcnow()
        return request_count, hour_start

    def _normalize_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        url = url.strip()
        if url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url or None

    def _map_row_to_seed(self, row: dict) -> InstitutionSeed:
        """Map a Scorecard API row to InstitutionSeed."""
        scorecard_id = str(row.get("id", ""))
        name = (row.get("school.name") or "").strip() or "Unknown"
        city = row.get("school.city") or row.get("location.city")
        state = row.get("school.state") or row.get("location.state")
        url = self._normalize_url(row.get("school.school_url"))
        ownership = row.get("school.ownership")
        public_private = OWNERSHIP_MAP.get(ownership) if ownership is not None else None
        return InstitutionSeed(
            name=name,
            country="United States",
            short_name=row.get("school.alias"),
            state_or_province=state,
            city=city,
            website_url=url,
            institution_type="university",
            public_private=public_private,
            ipeds_unit_id=None,
            scorecard_school_id=scorecard_id,
            data_source="college_scorecard",
        )

    def get_graduate_schools(
        self,
        per_page: int = 100,
        state: Optional[str] = None,
    ) -> Generator[InstitutionSeed, None, None]:
        """Fetch all US schools that offer graduate programs.

        Uses school.degrees_awarded.highest >= 3 (bachelor's) to include
        graduate-granting institutions. Respects 1000 req/hr rate limit.

        Args:
            per_page: Results per page (max 100).
            state: Optional state filter (e.g., 'CA', 'NY').

        Yields:
            InstitutionSeed for each school.
        """
        if not self.api_key:
            logger.warning("College Scorecard API key missing")
            return
        params: Dict[str, str] = {
            "api_key": self.api_key,
            "fields": ",".join(GRADUATE_SCHOOL_FIELDS),
            "school.degrees_awarded.highest__range": "3..4",
            "school.operating": "1",
            "per_page": str(min(per_page, 100)),
            "page": "0",
        }
        if state:
            params["school.state"] = state.upper()

        request_count = 0
        hour_start = datetime.utcnow()
        total_fetched = 0

        while True:
            request_count, hour_start = self._check_rate_limit(request_count, hour_start)
            response = self._get_client().get(SCORECARD_BASE_URL, params=params)
            response.raise_for_status()
            request_count += 1
            payload = response.json()
            results = payload.get("results", [])
            meta = payload.get("metadata", {})
            total = meta.get("total", 0)

            for row in results:
                try:
                    seed = self._map_row_to_seed(row)
                    if seed.name != "Unknown":
                        yield seed
                        total_fetched += 1
                except Exception as exc:
                    logger.debug("Skip invalid row: %s", exc)

            if total_fetched >= total or not results:
                break
            params["page"] = str(int(params["page"]) + 1)
            logger.info("Scorecard page %s, fetched %s/%s", params["page"], total_fetched, total)

