"""No-op Reviewer."""

from __future__ import annotations

from .base import ReviewResult, ReviewerProvider


class NoopReviewer(ReviewerProvider):
    name = "noop"

    def review(self, plan_md: str, diff: str) -> ReviewResult:
        return ReviewResult(
            approved=True,
            findings=[],
            summary="Noop reviewer: no checks performed.",
        )
