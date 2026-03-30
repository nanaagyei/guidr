"""Prompt registry: loads versioned templates by name."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptRegistry:
    """Load and manage versioned prompt templates.

    Templates are plain-text files in the templates/ directory,
    named as {name}_v{version}.txt (e.g., extraction_v1.txt).
    """

    _cache: dict[str, str] = {}

    @classmethod
    def get(cls, name: str, version: str = "v1") -> str:
        """Get a prompt template by name and version.

        Args:
            name: Template name (e.g., 'extraction', 'url_discovery', 'repair').
            version: Version string (default 'v1').

        Returns:
            Template string content.

        Raises:
            FileNotFoundError: If template file doesn't exist.
        """
        cache_key = f"{name}_{version}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        filename = f"{name}_{version}.txt"
        filepath = TEMPLATES_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Prompt template not found: {filepath}")

        content = filepath.read_text(encoding="utf-8")
        cls._cache[cache_key] = content
        return content

    @classmethod
    def render(cls, name: str, version: str = "v1", **kwargs: str) -> str:
        """Get and render a template with variable substitution.

        Uses Python str.format_map for {variable} placeholders.
        """
        template = cls.get(name, version)
        try:
            return template.format_map(kwargs)
        except KeyError as exc:
            logger.warning("Missing template variable %s in %s_%s", exc, name, version)
            return template

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
