"""Standalone Scrapy spider for crawling graduate program pages."""
import scrapy

from .items import ProgramItem


class SchoolsSpider(scrapy.Spider):
    name = "guidr_schools"
    custom_settings = {
        "ITEM_PIPELINES": {
            "scrapers.scrapy_project.pipelines.NormalizeFieldsPipeline": 300,
        },
        "USER_AGENT": "GuidrBot/1.0 (+https://guidr.app)",
        "DOWNLOAD_DELAY": 1.0,
    }

    def parse(self, response):
        yield ProgramItem(
            institution_unit_id=response.meta.get("unit_id"),
            program_name=response.css("h1::text").get(),
            degree_level=response.css(".degree::text").get(),
            field_of_study=response.css(".field::text").get(),
            description=" ".join(response.css("p::text").getall()),
        )

