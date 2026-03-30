import asyncio

from src.services.llm_extractor import LLMExtractor


def test_llm_extractor_fallback_program():
    extractor = LLMExtractor()
    html = "<html><body><h1>MS Computer Science</h1><p>Rigorous program.</p></body></html>"
    result = asyncio.run(extractor.extract_program_data(html, url="https://example.edu/program"))
    assert result["name"] == "MS Computer Science"
    assert result["description"]

