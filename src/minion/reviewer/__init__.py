"""Reviewer providers."""

from __future__ import annotations

from ..config import MinionConfig
from .base import ReviewerProvider, ReviewResult
from .noop import NoopReviewer

__all__ = ["ReviewerProvider", "ReviewResult", "NoopReviewer", "select_reviewer"]


def select_reviewer(cfg: MinionConfig) -> ReviewerProvider:
    if cfg.reviewer.provider == "noop":
        return NoopReviewer()
    return NoopReviewer()
