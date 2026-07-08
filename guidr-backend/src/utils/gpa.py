"""GPA normalization utilities."""
from decimal import Decimal


def normalize_gpa(gpa_value: float, gpa_scale: float) -> float:
    """Normalize GPA to 4.0 scale.

    Args:
        gpa_value: Raw GPA value
        gpa_scale: Scale of the GPA (e.g., 4.0, 10.0, 100.0)

    Returns:
        Normalized GPA on 4.0 scale
    """
    if gpa_scale == 0:
        return 0.0

    normalized = (gpa_value / gpa_scale) * 4.0
    return round(float(normalized), 2)
