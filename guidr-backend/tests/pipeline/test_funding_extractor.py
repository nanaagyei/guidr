"""Unit tests for FundingExtractor."""
import pytest

from src.pipeline.extractors.funding_extractor import FundingExtractor
from src.pipeline.schemas.funding_schemas import FundingType


class TestFundingExtractor:
    def test_extract_from_markdown_returns_list(self):
        extractor = FundingExtractor()
        result = extractor.extract_from_markdown("")
        assert result == []

    def test_extract_from_markdown_finds_fellowship(self):
        extractor = FundingExtractor()
        markdown = """
# Graduate Fellowship Program

Fellowship provides $25,000 per year to exceptional students.
Full tuition covered plus a stipend for living expenses.
        """
        items = extractor.extract_from_markdown(markdown)
        assert len(items) >= 1
        item = items[0]
        assert item.funding_type == FundingType.FELLOWSHIP
        assert "fellowship" in item.name.lower()

    def test_extract_from_markdown_finds_assistantship(self):
        extractor = FundingExtractor()
        markdown = """
# Teaching Assistantship (TA)

Assistantship positions provide $20,000 - $35,000 per year. Tuition remission included.
        """
        items = extractor.extract_from_markdown(markdown)
        assert len(items) >= 1
        item = items[0]
        assert item.funding_type == FundingType.ASSISTANTSHIP

    def test_classify_funding_type_fellowship(self):
        extractor = FundingExtractor()
        assert extractor.classify_funding_type("Predoctoral fellowship for PhD students") == FundingType.FELLOWSHIP

    def test_classify_funding_type_scholarship(self):
        extractor = FundingExtractor()
        assert extractor.classify_funding_type("Merit-based academic award") == FundingType.SCHOLARSHIP

    def test_parse_amount_single(self):
        extractor = FundingExtractor()
        min_val, max_val = extractor.parse_amount("Award amount: $30,000 per year")
        assert min_val == 30000
        assert max_val == 30000

    def test_parse_amount_range(self):
        extractor = FundingExtractor()
        min_val, max_val = extractor.parse_amount("Range: $20,000 - $35,000")
        assert min_val == 20000
        assert max_val == 35000

    def test_discover_funding_urls(self):
        extractor = FundingExtractor()
        links = [
            "https://example.edu/about",
            "https://example.edu/graduate/financial-aid",
            "https://example.edu/fellowships",
        ]
        funding = extractor.discover_funding_urls(links)
        assert len(funding) == 2
        assert any("financial-aid" in u for u in funding)
        assert any("fellowships" in u for u in funding)
