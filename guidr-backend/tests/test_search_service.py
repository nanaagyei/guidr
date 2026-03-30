from types import SimpleNamespace

from src.services.search_service import search_service


def test_serialize_institution_contains_key_fields():
    inst = SimpleNamespace(
        id="123",
        name="Sample U",
        country="USA",
        city="Boston",
        state_or_province="MA",
        short_name=None,
        website_url="https://sample.edu",
        institution_type="university",
        public_private="public",
        data_completeness_score=80,
    )
    payload = search_service.serialize_institution(inst)
    assert payload["name"] == "Sample U"
    assert payload["country"] == "USA"

