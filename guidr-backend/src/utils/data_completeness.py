"""Utility helpers to calculate data completeness scores."""
from __future__ import annotations

from typing import Iterable


def calculate_score(required_fields: Iterable[bool], optional_fields: Iterable[bool], required_weight: int, optional_weight: int) -> int:
    required_values = list(required_fields)
    optional_values = list(optional_fields)
    required_total = len(required_values) or 1
    optional_total = len(optional_values) or 1
    required_score = sum(1 for value in required_values if value) / required_total * required_weight
    optional_score = sum(1 for value in optional_values if value) / optional_total * optional_weight
    return int(round(required_score + optional_score))


def calculate_institution_completeness(data: dict) -> int:
    required = [bool(data.get("name")), bool(data.get("country")), bool(data.get("website_url"))]
    optional = [
        bool(data.get("city")),
        bool(data.get("state_or_province")),
        bool(data.get("institution_type")),
        bool(data.get("public_private")),
    ]
    return calculate_score(required, optional, required_weight=40, optional_weight=60)


def calculate_program_completeness(data: dict) -> int:
    required = [bool(data.get("name")), bool(data.get("degree_level")), bool(data.get("institution_id"))]
    optional = [
        bool(data.get("description")),
        bool(data.get("application_deadline_primary")),
        bool(data.get("tuition_estimate_per_year")),
        bool(data.get("program_features")),
    ]
    return calculate_score(required, optional, required_weight=50, optional_weight=50)

