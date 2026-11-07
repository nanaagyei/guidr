"""Errors raised by the Research Gateway."""
from __future__ import annotations


class ResearchProviderUnavailable(RuntimeError):
    """No real research provider is configured and synthetic output is not allowed.

    Raised in production instead of falling back to the stub provider, so that
    hard-coded programs, deadlines and funding amounts are never stored as real.
    """

    def __init__(
        self,
        message: str = "Research is temporarily unavailable. Nothing was generated.",
    ) -> None:
        super().__init__(message)
