"""IPEDS data fetcher."""
from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.scrapers import IPEDS_DATA_DIR
from src.scrapers.base import BaseFetcher, InstitutionSeed

logger = logging.getLogger(__name__)


ZIP_URL_TEMPLATE = "https://nces.ed.gov/ipeds/datacenter/data/HD{year}.zip"

SECTOR_PUBLIC_PRIVATE_MAP = {
    1: ("public", "degree_granting"),
    2: ("public", "degree_granting"),
    3: ("public", "degree_granting"),
    4: ("private", "degree_granting"),
    5: ("private", "degree_granting"),
    6: ("private", "degree_granting"),
    7: ("private", "non_degree"),
    8: ("public", "non_degree"),
    9: ("private", "non_degree"),
}


class IPEDSScraper(BaseFetcher):
    """Downloader and parser for the IPEDS directory dataset."""

    def __init__(
        self,
        *,
        data_dir: Path = IPEDS_DATA_DIR,
        timeout: int = 120,
    ) -> None:
        super().__init__(timeout=timeout)
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_directory_data(self, year: str = "2022", limit: Optional[int] = None) -> List[InstitutionSeed]:
        """Download the IPEDS directory CSV and normalize it."""
        csv_path = self._ensure_csv(year)
        df = pd.read_csv(csv_path, dtype=str, low_memory=False, encoding='latin-1')
        records: List[InstitutionSeed] = []
        for _, row in df.iterrows():
            record = self._row_to_institution(row)
            if record:
                records.append(record)
                if limit and len(records) >= limit:
                    break
        logger.info("Parsed %s IPEDS institutions for year %s", len(records), year)
        return records

    def _ensure_csv(self, year: str) -> Path:
        csv_path = self.data_dir / f"HD{year}.csv"
        if csv_path.exists():
            return csv_path
        zip_path = self.data_dir / f"HD{year}.zip"
        url = ZIP_URL_TEMPLATE.format(year=year)
        logger.info("Downloading IPEDS directory file %s", url)
        self.download_file(url, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            csv_name = next((name for name in zf.namelist() if name.lower().endswith(".csv")), None)
            if not csv_name:
                raise RuntimeError("IPEDS archive does not contain a CSV file")
            extracted_path = Path(zf.extract(csv_name, path=self.data_dir))
            extracted_path.rename(csv_path)
        return csv_path

    def _row_to_institution(self, row: pd.Series) -> Optional[InstitutionSeed]:
        name = (row.get("INSTNM") or "").strip()
        if not name:
            return None
        sector_raw = row.get("SECTOR")
        public_private = None
        institution_type = None
        if sector_raw:
            try:
                public_private, institution_type = SECTOR_PUBLIC_PRIVATE_MAP.get(int(float(sector_raw)), (None, None))
            except ValueError:
                public_private, institution_type = (None, None)
        return InstitutionSeed(
            name=name,
            short_name=(row.get("IALIAS") or None),
            country="USA",
            state_or_province=(row.get("STABBR") or None),
            city=(row.get("CITY") or None),
            website_url=self._normalize_url(row.get("WEBADDR")),
            institution_type=institution_type,
            public_private=public_private,
            ipeds_unit_id=(row.get("UNITID") or None),
            data_source="ipeds",
        )

    def _normalize_url(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = value.strip()
        if not value:
            return None
        if value.startswith("http"):
            return value
        return f"https://{value}"

