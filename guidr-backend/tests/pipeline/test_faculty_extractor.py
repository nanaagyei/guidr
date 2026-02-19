"""Unit tests for FacultyExtractor."""
import pytest

from src.pipeline.extractors.faculty_extractor import FacultyExtractor


class TestFacultyExtractor:
    def test_extract_from_markdown_returns_list(self):
        extractor = FacultyExtractor()
        result = extractor.extract_from_markdown("")
        assert result == []

    def test_extract_from_markdown_finds_professor(self):
        extractor = FacultyExtractor()
        markdown = """
## Dr. Jane Smith
Associate Professor
Email: jsmith@university.edu
Research interests: Machine learning, natural language processing
        """
        profs = extractor.extract_from_markdown(markdown)
        assert len(profs) >= 1
        prof = profs[0]
        assert "Smith" in prof.full_name
        assert prof.email == "jsmith@university.edu" or prof.email is None

    def test_clean_name_removes_prefix(self):
        extractor = FacultyExtractor()
        assert extractor.clean_name("Dr. John Doe") == "John Doe"
        assert extractor.clean_name("Prof. Jane Smith, Ph.D.") == "Jane Smith"

    def test_normalize_title(self):
        extractor = FacultyExtractor()
        assert extractor.normalize_title("lecturer") == "Lecturer"
        assert extractor.normalize_title("instructor") == "Instructor"

    def test_extract_email(self):
        extractor = FacultyExtractor()
        text = "Contact: john.doe@university.edu for more info"
        assert extractor.extract_email(text) == "john.doe@university.edu"

    def test_discover_faculty_urls(self):
        extractor = FacultyExtractor()
        links = [
            "https://example.edu/about",
            "https://example.edu/departments/cs/faculty",
            "https://example.edu/people/directory",
        ]
        faculty = extractor.discover_faculty_urls(links)
        assert len(faculty) == 2
