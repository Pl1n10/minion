"""Reviewer provider interface.

The Reviewer in the eventual workflow re-reads the Minion's diff and
checks it against the Teacher's plan. MVP defines only the contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ReviewResult:
    approved: bool
    findings: list[str]
    summary: str


class ReviewerProvider(ABC):
    name: str = "base"

    @abstractmethod
    def review(self, plan_md: str, diff: str) -> ReviewResult: ...
