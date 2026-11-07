"""Per-template allow-list of applicant personal fields that may reach a model provider.

Research is done on the program, not on the person (``docs/validation/ai-data-use.md``).
Every prompt template is listed here with the only personal fields it may receive. Nodes
that render templates must build their personal variables through
:func:`personal_template_vars`, so a field that is not on the list is never rendered.

Fields marked ``consent=True`` are rendered only when the applicant has recorded consent
(``user_profiles.ai_research_consent_at``). Without consent they render as a neutral
placeholder and the research runs on program-level inputs only.

Never allowed for any template: name, email, user id, citizenship, GPA, test scores, and
free text the applicant typed (career goals, program-style notes).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

MAX_KEYWORDS = 10
MAX_VALUE_LENGTH = 100


@dataclass(frozen=True)
class PersonalField:
    """A personal field a template may receive.

    Attributes:
        reason: One-line justification for sending it.
        consent: True when the field is rendered only with recorded consent.
        placeholder: Text rendered when the value is missing or consent is absent.
    """

    reason: str
    consent: bool
    placeholder: str = "Not specified"


# Template name -> {template variable -> PersonalField}. Templates with no personal fields
# are listed explicitly (empty dict) so the sentinel test covers every template.
PERSONAL_FIELD_ALLOWLIST: dict[str, dict[str, PersonalField]] = {
    "recommendation_run": {
        "degree_level": PersonalField(
            "Programs are filtered by the degree the applicant intends to take.", consent=False
        ),
        "field_of_study": PersonalField(
            "Programs are searched within the applicant's field.", consent=False
        ),
        "research_areas": PersonalField(
            "Keywords to match programs with relevant research groups.", consent=True
        ),
        "preferred_countries": PersonalField(
            "Where to search first.", consent=True, placeholder="Any"
        ),
        "funding_priority": PersonalField(
            "Coarse enum (high/medium/low) to weight funded programs.", consent=True
        ),
    },
    "funding_dossier": {
        "degree_level": PersonalField(
            "Funding differs between master's and doctoral programs.", consent=False
        ),
        "field_of_study": PersonalField(
            "External funding is searched within the field.", consent=False
        ),
    },
    "professor_synthesis": {
        "user_interests": PersonalField(
            "Research-area keywords to rank faculty by research fit.", consent=True
        ),
    },
    "school_dossier": {},
    "school_dossier_repair": {},
    "funding_dossier_repair": {},
    "recommendation_repair": {},
    "url_discovery": {},
    "extraction": {},
    "fill_missing": {},
    "repair": {},
    "synthesis": {},
}

# Maps the profile's funding_priority values to the coarse enum the prompt receives.
_FUNDING_PRIORITY = {
    "must_have": "high",
    "high": "high",
    "nice_to_have": "medium",
    "medium": "medium",
    "no_preference": "low",
    "low": "low",
}


def _clean(value: Any) -> str:
    """Return a trimmed, length-capped single-line string."""
    text = " ".join(str(value).split())
    return text[:MAX_VALUE_LENGTH]


def _keywords(values: Any) -> list[str]:
    """Return up to ``MAX_KEYWORDS`` cleaned, non-empty keyword strings."""
    if not isinstance(values, (list, tuple)):
        return []
    out = [_clean(v) for v in values if v and str(v).strip()]
    return out[:MAX_KEYWORDS]


def research_keywords(profile: Mapping[str, Any], consented: bool) -> list[str]:
    """Research-area keywords that may be sent outside the process.

    Used both for the professor synthesis prompt and the OpenAlex author search.

    Args:
        profile: Minimised profile mapping (see ``minimised_profile``).
        consented: Whether the applicant has recorded AI research consent.

    Returns:
        Cleaned keywords, or an empty list without consent.
    """
    if not consented:
        return []
    return _keywords(profile.get("research_areas"))


def _render_value(name: str, profile: Mapping[str, Any]) -> Optional[str]:
    """Render one allow-listed field from the profile, or None when empty."""
    if name == "funding_priority":
        raw = str(profile.get("funding_priority") or "").strip().lower()
        return _FUNDING_PRIORITY.get(raw)
    if name in ("research_areas", "preferred_countries", "user_interests"):
        key = "research_areas" if name == "user_interests" else name
        items = _keywords(profile.get(key))
        return ", ".join(items) or None
    value = profile.get(name)
    if value is None or not str(value).strip():
        return None
    return _clean(value)


def personal_template_vars(
    template_name: str, profile: Optional[Mapping[str, Any]], consented: bool
) -> dict[str, str]:
    """Build the personal template variables a template is allowed to receive.

    Args:
        template_name: Template name without version (e.g. ``"recommendation_run"``).
        profile: Minimised profile mapping; other keys are ignored.
        consented: Whether the applicant has recorded AI research consent.

    Returns:
        A mapping containing exactly the allow-listed fields for the template. Fields
        that need consent render as their placeholder when consent is absent.

    Raises:
        KeyError: If the template has no allow-list entry.
    """
    allowed = PERSONAL_FIELD_ALLOWLIST[template_name]
    profile = profile or {}
    out: dict[str, str] = {}
    for name, spec in allowed.items():
        value = None if (spec.consent and not consented) else _render_value(name, profile)
        out[name] = value or spec.placeholder
    return out


def minimised_profile(profile: Any) -> dict[str, Any]:
    """Copy only the profile fields any template may use, plus the consent flag.

    Args:
        profile: A ``UserProfile`` row (or any object with the same attributes).

    Returns:
        A dict safe to keep in pipeline state. GPA, citizenship, free text and
        identifiers are never copied.
    """
    return {
        "degree_level": getattr(profile, "intended_degree", None),
        "field_of_study": getattr(profile, "primary_field_of_study", None),
        "research_areas": list(getattr(profile, "research_areas", None) or []),
        "preferred_countries": list(getattr(profile, "preferred_countries", None) or []),
        "funding_priority": getattr(profile, "funding_priority", None),
        "ai_research_consent": getattr(profile, "ai_research_consent_at", None) is not None,
    }
