"""Unit tests for OverviewExtractor."""
import pytest

from src.pipeline.extractors.overview_extractor import OverviewExtractor


class TestOverviewExtractor:
    def test_extract_from_markdown_empty_returns_default(self):
        extractor = OverviewExtractor()
        result = extractor.extract_from_markdown("")
        assert result.description is None
        assert result.acceptance_rate is None

    def test_extract_acceptance_rate(self):
        extractor = OverviewExtractor()
        text = "Acceptance rate: 15.5% for graduate programs."
        assert extractor.extract_acceptance_rate(text) == 15.5

    def test_extract_enrollment(self):
        extractor = OverviewExtractor()
        text = "Total enrollment: 25,000 students"
        assert extractor.extract_enrollment(text) == 25000

    def test_extract_grad_enrollment(self):
        extractor = OverviewExtractor()
        text = "Graduate student enrollment: 8,500"
        assert extractor.extract_grad_enrollment(text) == 8500

    def test_detect_campus_setting_urban(self):
        extractor = OverviewExtractor()
        text = "Located in an urban metropolitan area"
        assert extractor.detect_campus_setting(text) == "urban"

    def test_detect_academic_calendar_semester(self):
        extractor = OverviewExtractor()
        text = "We operate on a semester system with two semesters per year"
        assert extractor.detect_academic_calendar(text) == "semester"

    def test_extract_from_markdown_full_page(self):
        extractor = OverviewExtractor()
        markdown = """
# About Our University

We are a leading research institution. Our suburban campus is located in a quiet suburb.

Acceptance rate: 18.2%
Total enrollment: 30,000
Graduate student enrollment: 12,000

The suburban campus offers a semester-based academic calendar.
        """
        result = extractor.extract_from_markdown(markdown)
        assert result.acceptance_rate == 18.2
        assert result.enrollment_total == 30000
        assert result.grad_enrollment == 12000
        assert result.academic_calendar == "semester"
