"""Validator: schema validation and business rules for pipeline data.

Outputs: passed, failed, warning. Failed records are rejected; warning records
can proceed but are flagged for review.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a single record."""

    passed: bool
    status: str  # "passed", "failed", "warning"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DataValidator:
    """Validates extracted data against schema and business rules."""

    def validate_funding(
        self,
        data: Dict[str, Any],
    ) -> ValidationResult:
        """Validate funding opportunity data."""
        errors: List[str] = []
        warnings: List[str] = []

        name = data.get("name") or ""
        if len(name) < 2:
            errors.append("name too short")
        if len(name) > 500:
            errors.append("name too long")

        funding_type = data.get("funding_type")
        valid_types = {"fellowship", "assistantship", "scholarship", "grant", "waiver"}
        if funding_type and funding_type.lower() not in valid_types:
            errors.append(f"invalid funding_type: {funding_type}")

        amount_min = data.get("amount_min")
        amount_max = data.get("amount_max")
        if amount_min is not None and (amount_min < 0 or amount_min > 100_000):
            warnings.append("amount_min outside typical range (0-100k)")
        if amount_max is not None and (amount_max < 0 or amount_max > 100_000):
            warnings.append("amount_max outside typical range (0-100k)")
        if amount_min is not None and amount_max is not None and amount_min > amount_max:
            errors.append("amount_min > amount_max")

        deadline = data.get("deadline")
        if deadline and isinstance(deadline, (date, str)):
            try:
                d = date.fromisoformat(str(deadline)[:10]) if isinstance(deadline, str) else deadline
                if d < date.today():
                    warnings.append("deadline is in the past")
            except (ValueError, TypeError):
                pass

        if errors:
            return ValidationResult(passed=False, status="failed", errors=errors, warnings=warnings)
        if warnings:
            return ValidationResult(passed=True, status="warning", errors=[], warnings=warnings)
        return ValidationResult(passed=True, status="passed", errors=[], warnings=[])

    def validate_program(
        self,
        data: Dict[str, Any],
    ) -> ValidationResult:
        """Validate program data."""
        errors: List[str] = []
        warnings: List[str] = []

        name = data.get("name") or ""
        if len(name) < 2:
            errors.append("name too short")
        if len(name) > 500:
            errors.append("name too long")

        degree_level = data.get("degree_level")
        if degree_level and degree_level.lower() not in {"phd", "masters", "certificate", "professional", "unknown"}:
            warnings.append(f"unusual degree_level: {degree_level}")

        gpa = data.get("minimum_gpa")
        if gpa is not None and (gpa < 0 or gpa > 4.0):
            errors.append("minimum_gpa must be 0-4.0")

        if errors:
            return ValidationResult(passed=False, status="failed", errors=errors, warnings=warnings)
        if warnings:
            return ValidationResult(passed=True, status="warning", errors=[], warnings=warnings)
        return ValidationResult(passed=True, status="passed", errors=[], warnings=[])

    def validate_faculty(
        self,
        data: Dict[str, Any],
    ) -> ValidationResult:
        """Validate faculty/professor data."""
        errors: List[str] = []
        warnings: List[str] = []

        name = data.get("full_name") or data.get("name") or ""
        if len(name) < 3:
            errors.append("name too short")
        if " " not in name:
            warnings.append("name may be incomplete (no space)")

        if errors:
            return ValidationResult(passed=False, status="failed", errors=errors, warnings=warnings)
        if warnings:
            return ValidationResult(passed=True, status="warning", errors=[], warnings=warnings)
        return ValidationResult(passed=True, status="passed", errors=[], warnings=[])

    def validate_overview(
        self,
        data: Dict[str, Any],
    ) -> ValidationResult:
        """Validate institution overview data."""
        errors: List[str] = []
        warnings: List[str] = []

        acceptance_rate = data.get("acceptance_rate")
        if acceptance_rate is not None and (acceptance_rate < 0 or acceptance_rate > 100):
            errors.append("acceptance_rate must be 0-100")

        if errors:
            return ValidationResult(passed=False, status="failed", errors=errors, warnings=warnings)
        return ValidationResult(passed=True, status="passed", errors=[], warnings=warnings)

    def validate_generic(
        self,
        entity_kind: str,
        data: Dict[str, Any],
    ) -> ValidationResult:
        """Dispatch validation by entity kind."""
        dispatch = {
            "school": self.validate_overview,
            "program": self.validate_program,
            "professor": self.validate_faculty,
            "funding": self.validate_funding,
        }
        validator_fn = dispatch.get(entity_kind)
        if validator_fn is None:
            logger.warning("No validator for entity_kind=%s", entity_kind)
            return ValidationResult(passed=True, status="passed")
        return validator_fn(data)
