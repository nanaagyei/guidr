"""Scrapy pipelines for cleaning and persistence."""
from __future__ import annotations

from itemadapter import ItemAdapter


class NormalizeFieldsPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        for field_name, value in list(adapter.items()):
            if isinstance(value, str):
                adapter[field_name] = value.strip()
        return item
