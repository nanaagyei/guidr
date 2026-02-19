"""Transformer: normalize and clean extracted data for production schema.

Handles: date parsing, text cleanup, currency normalization, reference resolution.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DataTransformer:
    """Transforms raw extracted data to production-ready format."""

    def transform_text(self, value: Optional[str]) -> Optional[str]:
        """Clean and normalize text."""
        if value is None:
            return None
        if not isinstance(value, str):
            return str(value).strip() or None
        # Remove excessive whitespace, HTML artifacts
        text = re.sub(r"\s+", " ", value.strip())
        text = re.sub(r"<[^>]+>", "", text)
        return text if text else None

    def transform_funding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform funding data for production."""
        out = dict(data)
        if out.get("description"):
            out["description"] = self.transform_text(out["description"])
        if out.get("eligibility_criteria"):
            out["eligibility_criteria"] = self.transform_text(out["eligibility_criteria"])
        if "amount_min" in out and out["amount_min"] is not None:
            try:
                out["amount_min"] = Decimal(str(out["amount_min"]))
            except (ValueError, TypeError):
                out["amount_min"] = None
        if "amount_max" in out and out["amount_max"] is not None:
            try:
                out["amount_max"] = Decimal(str(out["amount_max"]))
            except (ValueError, TypeError):
                out["amount_max"] = None
        if out.get("deadline") and isinstance(out["deadline"], str):
            try:
                out["deadline"] = date.fromisoformat(out["deadline"][:10])
            except (ValueError, TypeError):
                out["deadline"] = None
        return out

    def transform_program(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform program data for production."""
        out = dict(data)
        if out.get("description"):
            out["description"] = self.transform_text(out["description"])
        if out.get("name"):
            out["name"] = self.transform_text(out["name"]) or out["name"]
        if "minimum_gpa" in out and out["minimum_gpa"] is not None:
            try:
                out["minimum_gpa"] = round(float(out["minimum_gpa"]), 2)
            except (ValueError, TypeError):
                out["minimum_gpa"] = None
        if out.get("application_deadline_primary") and isinstance(out["application_deadline_primary"], str):
            try:
                out["application_deadline_primary"] = date.fromisoformat(out["application_deadline_primary"][:10])
            except (ValueError, TypeError):
                out["application_deadline_primary"] = None
        return out

    def transform_faculty(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform faculty data for production."""
        out = dict(data)
        name = out.get("full_name") or out.get("name")
        if name:
            out["full_name"] = self.transform_text(name) or name
        if out.get("email"):
            out["email"] = self.transform_text(out["email"])
        return out

    def transform_overview(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform overview data for production."""
        out = dict(data)
        if out.get("description"):
            out["description"] = self.transform_text(out["description"])
        return out
