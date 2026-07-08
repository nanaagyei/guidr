"""Prompt registry: loads versioned templates with A/B variant support."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptRegistry:
    """Load and manage versioned prompt templates with A/B variant support.

    Templates are plain-text files in the templates/ directory,
    named as {name}_{version}.txt (e.g., extraction_v1.txt).

    Variants follow the pattern {name}_{version}_{variant}.txt
    (e.g., extraction_v1_b.txt). The default (no suffix) is variant "a".
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
    def list_variants(cls, name: str, version: str = "v1") -> list[str]:
        """List all available variants for a template.

        Returns variant identifiers (e.g., ["a", "b"]).
        The default template (no suffix) counts as variant "a".
        """
        variants: list[str] = []

        # Check for the default (variant "a")
        default_path = TEMPLATES_DIR / f"{name}_{version}.txt"
        if default_path.exists():
            variants.append("a")

        # Scan for variant files: {name}_{version}_{variant}.txt
        pattern = f"{name}_{version}_*.txt"
        for path in TEMPLATES_DIR.glob(pattern):
            stem = path.stem  # e.g., "extraction_v1_b"
            suffix = stem.removeprefix(f"{name}_{version}_")
            if suffix and suffix != stem:
                variants.append(suffix)

        return sorted(variants)

    @classmethod
    def get_with_variant(
        cls,
        name: str,
        version: str = "v1",
        variant_seed: Optional[str] = None,
    ) -> tuple[str, str]:
        """Get a template with deterministic A/B variant selection.

        Uses a hash of ``variant_seed`` to deterministically pick a variant
        from those available.  Returns ``(template_content, variant_id)``.

        If only one variant exists (the default), it is always returned.
        If ``variant_seed`` is None, the default variant is returned.
        """
        variants = cls.list_variants(name, version)
        if not variants:
            raise FileNotFoundError(
                f"No prompt variants found for {name}_{version}"
            )

        # Single variant or no seed → default
        if len(variants) == 1 or variant_seed is None:
            variant = variants[0]
        else:
            # Deterministic selection via hash
            digest = hashlib.md5(variant_seed.encode()).hexdigest()
            idx = int(digest, 16) % len(variants)
            variant = variants[idx]

        # Load the correct file
        if variant == "a":
            content = cls.get(name, version)
        else:
            cache_key = f"{name}_{version}_{variant}"
            if cache_key in cls._cache:
                content = cls._cache[cache_key]
            else:
                filename = f"{name}_{version}_{variant}.txt"
                filepath = TEMPLATES_DIR / filename
                if not filepath.exists():
                    raise FileNotFoundError(
                        f"Variant template not found: {filepath}"
                    )
                content = filepath.read_text(encoding="utf-8")
                cls._cache[cache_key] = content

        return content, variant

    @classmethod
    def render_with_variant(
        cls,
        name: str,
        version: str = "v1",
        variant_seed: Optional[str] = None,
        **kwargs: str,
    ) -> tuple[str, str]:
        """Render a template with A/B variant selection.

        Returns ``(rendered_content, variant_id)``.
        """
        template, variant = cls.get_with_variant(name, version, variant_seed)
        try:
            rendered = template.format_map(kwargs)
        except KeyError as exc:
            logger.warning("Missing template variable %s in %s_%s", exc, name, version)
            rendered = template
        return rendered, variant

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
