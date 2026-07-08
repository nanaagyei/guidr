"""Scrapy spider entrypoints for school websites."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import scrapy

from src.scrapers import RAW_DATA_DIR


class SchoolProgramsSpider(scrapy.Spider):
    """Scrapy spider placeholder that captures program pages."""

    name = "school_programs"

    custom_settings = {
        "DOWNLOAD_DELAY": 1.0,
        "USER_AGENT": "GuidrBot/1.0 (+https://guidr.app)",
        "FEEDS": {
            str(RAW_DATA_DIR / "school_programs.jsonl"): {
                "format": "jsonlines",
            }
        },
    }

    def start_requests(self) -> Iterable[scrapy.Request]:
        for url in getattr(self, "start_urls", []):
            yield scrapy.Request(url=url, callback=self.parse_programs)

    def parse_programs(self, response: scrapy.http.Response):
        yield {
            "url": response.url,
            "title": response.css("title::text").get(),
            "raw_html_path": self._persist_raw_html(response),
        }

    def _persist_raw_html(self, response: scrapy.http.Response) -> str:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        slug = response.url.replace("https://", "").replace("http://", "").replace("/", "_")
        file_path = RAW_DATA_DIR / f"{slug}.html"
        file_path.write_bytes(response.body)
        return str(file_path)
