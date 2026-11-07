"""Applicants' personal data must not reach research model providers (issue #92).

Renders every prompt template with a profile full of sentinel values and checks that only
allow-listed (and, where required, consented) fields appear. Then runs the dossier and
professor nodes against real provider adapters with a mocked HTTP client and inspects the
request bodies for identifiers.
"""
import json
import re
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.prompts.personal_fields import (
    PERSONAL_FIELD_ALLOWLIST,
    minimised_profile,
    personal_template_vars,
)
from src.pipeline.prompts.registry import TEMPLATES_DIR, PromptRegistry

USER_ID = "550e8400-e29b-41d4-a716-4466554400aa"
SCHOOL_ID = "550e8400-e29b-41d4-a716-446655440000"

# Profile attribute -> sentinel. Lists hold one sentinel each.
SENTINEL_PROFILE = {
    "intended_degree": "SENTINEL-DEGREE",
    "primary_field_of_study": "SENTINEL-FIELD",
    "research_areas": ["SENTINEL-RESEARCH"],
    "preferred_countries": ["SENTINEL-COUNTRY"],
    "funding_priority": "must_have",  # coarse enum; rendered as "high"
    "secondary_fields": ["SENTINEL-SECONDARY"],
    "preferred_cities": ["SENTINEL-CITY"],
    "career_goals": "SENTINEL-CAREER call me at SENTINEL-EMAIL@example.com",
    "program_style_preference": "SENTINEL-FREETEXT",
    "country_of_citizenship": "SENTINEL-CITIZENSHIP",
    "current_country": "SENTINEL-CURRENT-COUNTRY",
    "current_city": "SENTINEL-CURRENT-CITY",
    "gpa": "SENTINEL-GPA",
    "normalized_gpa": "SENTINEL-GPA",
    "test_scores": "SENTINEL-TESTSCORE",
    "full_name": "SENTINEL-NAME",
    "email": "SENTINEL-EMAIL@example.com",
    "user_id": USER_ID,
}

# Sentinel each allow-listed template variable carries when rendered.
ALLOWED_SENTINEL = {
    "degree_level": "SENTINEL-DEGREE",
    "field_of_study": "SENTINEL-FIELD",
    "research_areas": "SENTINEL-RESEARCH",
    "user_interests": "SENTINEL-RESEARCH",
    "preferred_countries": "SENTINEL-COUNTRY",
}

ALL_SENTINELS = {
    v for v in json.dumps(SENTINEL_PROFILE).split('"') if v.startswith("SENTINEL-")
} | {"SENTINEL-EMAIL@example.com", USER_ID}

# Never sent by any template, consent or not.
FORBIDDEN = [
    "SENTINEL-GPA",
    "SENTINEL-CITIZENSHIP",
    "SENTINEL-EMAIL",
    "SENTINEL-NAME",
    "SENTINEL-CAREER",
    "SENTINEL-FREETEXT",
    "SENTINEL-SECONDARY",
    "SENTINEL-CITY",
    "SENTINEL-CURRENT",
    "SENTINEL-TESTSCORE",
    USER_ID,
]

# Template variables that describe the program, school or extracted content, never the
# applicant. Any other placeholder must be on the template's personal allow-list.
PROGRAM_VARS = {
    "category", "content", "entity_name", "entity_type", "source_url",
    "current_extracted_json", "missing_fields", "low_confidence_fields", "previous_json",
    "existing_funding", "program_name", "school_name", "candidates_json", "department",
    "error_message", "previous_url", "existing_data", "school_website", "extracted_json",
    "website_hint",
}


def _profile(consented: bool) -> SimpleNamespace:
    return SimpleNamespace(
        **SENTINEL_PROFILE,
        ai_research_consent_at=datetime(2026, 11, 7) if consented else None,
    )


def _template_names() -> list[str]:
    names = set()
    for path in TEMPLATES_DIR.glob("*.txt"):
        names.add(re.sub(r"_v\d+(_[a-z0-9]+)?$", "", path.stem))
    return sorted(names)


def _placeholders(name: str) -> set[str]:
    return set(re.findall(r"(?<!\{)\{([a-z_]+)\}(?!\})", PromptRegistry.get(name, "v1")))


def _assert_no_forbidden(text: str) -> None:
    for sentinel in FORBIDDEN:
        assert sentinel not in text, f"{sentinel} reached the provider"


class TestAllowList:
    def test_every_template_has_an_allowlist(self):
        missing = [n for n in _template_names() if n not in PERSONAL_FIELD_ALLOWLIST]
        assert not missing, f"templates without a personal-field allow-list: {missing}"

    @pytest.mark.parametrize("name", _template_names())
    def test_placeholders_are_program_level_or_allowlisted(self, name):
        personal = _placeholders(name) - PROGRAM_VARS
        assert personal <= set(PERSONAL_FIELD_ALLOWLIST[name]), (
            f"{name} has personal placeholders not on its allow-list: "
            f"{personal - set(PERSONAL_FIELD_ALLOWLIST[name])}"
        )

    def test_default_allowlist_matches_owner_decision(self):
        assert set(PERSONAL_FIELD_ALLOWLIST["recommendation_run"]) == {
            "degree_level", "field_of_study", "research_areas", "preferred_countries",
            "funding_priority",
        }
        assert set(PERSONAL_FIELD_ALLOWLIST["funding_dossier"]) == {
            "degree_level", "field_of_study",
        }
        assert set(PERSONAL_FIELD_ALLOWLIST["professor_synthesis"]) == {"user_interests"}

    def test_minimised_profile_never_copies_sensitive_fields(self):
        _assert_no_forbidden(json.dumps(minimised_profile(_profile(consented=True))))


class TestSentinelRender:
    @pytest.mark.parametrize("consented", [True, False])
    @pytest.mark.parametrize("name", _template_names())
    def test_only_allowlisted_sentinels_render(self, name, consented):
        allowed = PERSONAL_FIELD_ALLOWLIST[name]
        program = {v: f"PROGRAM-{v}" for v in PROGRAM_VARS}
        personal = personal_template_vars(
            name, minimised_profile(_profile(consented)), consented=consented
        )
        values = {**program, **personal}
        # Substitute known placeholders only: some unused templates (fill_missing,
        # synthesis) contain unescaped JSON braces that str.format_map rejects.
        rendered = re.sub(
            r"(?<!\{)\{([a-z_]+)\}(?!\})",
            lambda m: values.get(m.group(1), m.group(0)),
            PromptRegistry.get(name, "v1"),
        )

        _assert_no_forbidden(rendered)
        expected = {
            ALLOWED_SENTINEL[var]
            for var, spec in allowed.items()
            if var in ALLOWED_SENTINEL and (consented or not spec.consent)
        }
        present = {s for s in ALL_SENTINELS if s in rendered}
        assert present == expected
        if "funding_priority" in allowed:
            assert ("Funding Priority: high" in rendered) is consented


def _capture_gateway():
    """Patch ResearchGatewayService so nodes hand their request to a list."""
    captured = []

    class FakeService:
        def run(self, request):
            captured.append(request)
            from src.pipeline.research_gateway.schemas import DossierResponse
            return DossierResponse(status="SUCCESS", final_json={})

    return captured, patch("src.pipeline.research_gateway.ResearchGatewayService", FakeService)


def _db_returning(*rows):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = list(rows)
    return db


class TestNodesSendOnlyAllowlistedFields:
    @pytest.mark.parametrize("consented", [True, False])
    @patch("src.pipeline.orchestrator.dossier_nodes._get_db")
    def test_recommendation_run(self, mock_get_db, consented):
        from src.pipeline.orchestrator.dossier_nodes import load_dossier_context, research_extract

        mock_get_db.return_value = _db_returning(_profile(consented))
        state = {"job_type": "recommendation_run", "user_id": USER_ID, "progress": []}
        state.update(load_dossier_context(state))

        captured, patcher = _capture_gateway()
        with patcher:
            research_extract(state)

        prompt = captured[0].prompt_override
        _assert_no_forbidden(prompt)
        _assert_no_forbidden(json.dumps(state["user_profile"]))
        assert "SENTINEL-DEGREE" in prompt and "SENTINEL-FIELD" in prompt
        for gated in ("SENTINEL-RESEARCH", "SENTINEL-COUNTRY"):
            assert (gated in prompt) is consented

    def test_funding_dossier_never_sends_citizenship_even_if_loaded(self):
        """The latent path: a full profile in state still renders no citizenship."""
        from src.pipeline.orchestrator.dossier_nodes import research_extract

        state = {
            "job_type": "funding_dossier",
            "entity_name": "PROGRAM-SCHOOL",
            "user_profile": {
                **{k: v for k, v in SENTINEL_PROFILE.items()},
                "field_of_study": "SENTINEL-FIELD",
                "ai_research_consent": True,
            },
            "progress": [],
        }
        captured, patcher = _capture_gateway()
        with patcher:
            research_extract(state)

        prompt = captured[0].prompt_override
        _assert_no_forbidden(prompt)
        assert "SENTINEL-RESEARCH" not in prompt
        assert "SENTINEL-FIELD" in prompt

    @pytest.mark.parametrize("consented", [True, False])
    @patch("src.pipeline.clients.openalex.OpenAlexClient")
    @patch("src.pipeline.orchestrator.professor_nodes._get_db")
    def test_professor_match(self, mock_get_db, MockOpenAlex, consented):
        from src.pipeline.orchestrator.professor_nodes import (
            load_professor_context,
            query_openalex,
            synthesize_rank,
        )

        inst = SimpleNamespace(name="PROGRAM-SCHOOL")
        mock_get_db.return_value = _db_returning(inst, _profile(consented))
        state = {
            "entity_id": SCHOOL_ID,
            "user_id": USER_ID,
            "user_interests": ["SENTINEL-RESEARCH", "SENTINEL-CAREER from job input"],
            "progress": [],
        }
        state.update(load_professor_context(state))

        MockOpenAlex.return_value.search_authors.return_value = []
        state.update(query_openalex(state))
        query = MockOpenAlex.return_value.search_authors.call_args.kwargs["query"]

        state["enriched_candidates"] = []
        captured, patcher = _capture_gateway()
        with patcher:
            synthesize_rank(state)
        prompt = captured[0].prompt_override

        for outbound in (query, prompt):
            assert ("SENTINEL-RESEARCH" in outbound) is consented
        # Job-input interests are only research keywords; they are cleaned, not trusted.
        assert USER_ID not in prompt and USER_ID not in query
        assert "SENTINEL-GPA" not in prompt and "SENTINEL-CITIZENSHIP" not in prompt


def _mock_http_client():
    client = MagicMock()
    response = MagicMock()
    response.json.return_value = {
        "choices": [{"message": {"content": "{}"}}],
        "citations": [],
    }
    response.raise_for_status.return_value = None
    client.post.return_value = response
    return client


class TestProviderPayload:
    """Request bodies sent to real provider adapters carry no applicant identifiers."""

    @pytest.fixture(params=["perplexity", "open_deep_research"])
    def provider(self, request):
        if request.param == "perplexity":
            from src.pipeline.research_gateway.providers.perplexity import PerplexityProvider
            p = PerplexityProvider(api_key="test-key")
        else:
            from src.pipeline.research_gateway.providers.open_deep_research import (
                OpenDeepResearchProvider,
            )
            p = OpenDeepResearchProvider(api_key="test-key", base_url="https://odr.invalid/v1")
        p._client = _mock_http_client()
        return p

    @patch("src.pipeline.research_gateway.service.ResearchGatewayService._cache_set")
    @patch("src.pipeline.research_gateway.service.ResearchGatewayService._cache_get")
    @patch("src.pipeline.orchestrator.dossier_nodes._get_db")
    def test_recommendation_payload_has_no_identifiers(
        self, mock_get_db, mock_cache_get, _mock_cache_set, provider
    ):
        from src.pipeline.orchestrator.dossier_nodes import load_dossier_context, research_extract

        mock_cache_get.return_value = None
        mock_get_db.return_value = _db_returning(_profile(consented=True))
        state = {"job_type": "recommendation_run", "user_id": USER_ID, "progress": []}
        state.update(load_dossier_context(state))

        with patch(
            "src.pipeline.research_gateway.service._select_provider", return_value=provider
        ):
            research_extract(state)

        assert provider._client.post.called
        for call in provider._client.post.call_args_list:
            body = json.dumps(call.kwargs.get("json"))
            headers = json.dumps(call.kwargs.get("headers"))
            url = str(call.args[0] if call.args else call.kwargs.get("url"))
            for outbound in (body, headers, url):
                _assert_no_forbidden(outbound)
            assert "SENTINEL-RESEARCH" in body  # consented field does go out

        # The cache key is a local hash and carries no identifier either.
        dedupe = mock_cache_get.call_args.args[0]
        assert USER_ID not in dedupe


class TestCacheKey:
    def test_different_prompts_get_different_keys(self):
        from src.pipeline.research_gateway.schemas import EntityContext, ResearchRequest
        from src.pipeline.research_gateway.service import _dedupe_key

        def req(prompt):
            return ResearchRequest(
                job_type="RECOMMENDATION_RUN",
                entity=EntityContext(entity_type="SCHOOL"),
                category="recommendation_run",
                prompt_override=prompt,
            )

        assert _dedupe_key(req("a")) != _dedupe_key(req("b"))
        assert _dedupe_key(req("a")) == _dedupe_key(req("a"))
