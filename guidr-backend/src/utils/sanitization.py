"""Shared input sanitization and normalization utilities."""
import re
from typing import Any, Union

# Allowlist for text inputs that feed into LLM prompts.
# Permits: word chars, whitespace, hyphens, commas, dots, slashes,
# parentheses, ampersands, apostrophes.
SAFE_TEXT_PATTERN = re.compile(r"^[\w\s\-,./()&']+$")


def sanitize_text(value: str, max_length: int = 200) -> str:
    """Strip whitespace and truncate to max_length."""
    return value.strip()[:max_length]


def validate_safe_text(value: str) -> bool:
    """Return True if value matches the safe text allowlist."""
    return bool(SAFE_TEXT_PATTERN.match(value))


def normalize_string_list(
    value: Any,
    *,
    max_items: int = 30,
    max_item_length: int = 100,
) -> list[str]:
    """Normalize a value into a deduplicated list of trimmed strings.

    Accepts:
      - A comma-separated string: "A, B, C" -> ["A", "B", "C"]
      - A list of strings: ["A", " B ", "C"] -> ["A", "B", "C"]
      - None or empty -> []

    Deduplicates case-insensitively (keeps first occurrence).
    Truncates items to max_item_length and limits total count to max_items.
    """
    if value is None:
        return []

    # Convert comma-separated string to list
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, list):
        items = value
    else:
        return []

    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        if not isinstance(item, str):
            continue
        # Collapse multiple internal spaces to single space
        cleaned = " ".join(item.split()).strip()
        if not cleaned:
            continue
        # Truncate to max length
        cleaned = cleaned[:max_item_length]
        # Case-insensitive dedup
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= max_items:
            break

    return result
