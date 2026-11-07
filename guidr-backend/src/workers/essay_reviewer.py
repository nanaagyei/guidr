"""Worker job for reviewing essays.

Essay review is not available yet. The previous placeholder wrote fixed scores and
canned feedback; it was removed so that synthetic reviews can never be stored.
"""


def review_essay(essay_id: str, attempt: int = 1):
    """Review an essay (not implemented).

    When built, this must provide feedback only and never rewrite the essay.

    Args:
        essay_id: Essay UUID as string
        attempt: Attempt number for retries

    Raises:
        NotImplementedError: Always.
    """
    raise NotImplementedError("Essay review is not available yet")
