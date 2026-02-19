"""Unit tests for ProgramExtractor."""
import pytest

from src.pipeline.extractors.program_extractor import ProgramExtractor


class TestProgramExtractor:
    def test_extract_from_markdown_returns_list(self):
        extractor = ProgramExtractor()
        result = extractor.extract_from_markdown("")
        assert result == []

    def test_extract_from_markdown_finds_program(self):
        extractor = ProgramExtractor()
        markdown = """
# Master of Science in Computer Science

The MS in Computer Science is a 24-month program. Minimum GPA 3.0.
GRE required. Application deadline: January 15, 2026.
Tuition: $45,000 per year.
        """
        programs = extractor.extract_from_markdown(markdown)
        assert len(programs) >= 1
        prog = programs[0]
        assert "Computer Science" in prog.name or "Science" in prog.name
        assert prog.degree_level == "masters"

    def test_detect_degree_level_phd(self):
        extractor = ProgramExtractor()
        assert extractor.detect_degree_level("PhD program in Biology") == "phd"

    def test_extract_gpa(self):
        extractor = ProgramExtractor()
        assert extractor.extract_gpa("Minimum GPA: 3.5 required") == 3.5

    def test_extract_gre_required(self):
        extractor = ProgramExtractor()
        assert extractor.extract_gre_required("GRE required for admission") is True
        assert extractor.extract_gre_required("GRE optional") is False
