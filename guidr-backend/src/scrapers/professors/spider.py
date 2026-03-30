"""Scrapy spider placeholder for professor directories."""
import scrapy


class ProfessorDirectorySpider(scrapy.Spider):
    name = "professor_directory"

    def parse(self, response):
        yield {"url": response.url}

