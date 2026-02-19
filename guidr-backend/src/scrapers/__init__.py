"""Scraping utilities and data source integrations."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
IPEDS_DATA_DIR = DATA_DIR / "ipeds"


__all__ = [
    "DATA_DIR",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "IPEDS_DATA_DIR",
]

