"""Scrapy item definitions."""
import scrapy


class SchoolItem(scrapy.Item):
    unit_id = scrapy.Field()
    name = scrapy.Field()
    city = scrapy.Field()
    state = scrapy.Field()
    website = scrapy.Field()


class ProgramItem(scrapy.Item):
    institution_unit_id = scrapy.Field()
    program_name = scrapy.Field()
    degree_level = scrapy.Field()
    field_of_study = scrapy.Field()
    description = scrapy.Field()
