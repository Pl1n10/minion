"""Teacher provider interface.

The Teacher's job in the eventual workflow is to turn a high-level task
into a structured plan (acceptance criteria, suggested touch points,
risks). For the MVP we only define the contract; a real implementation
will plug into a cloud LLM.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TeacherPlan:
    task: str
    summary: str
    steps: list[str]
    acceptance: list[str]
    risks: list[str]


class TeacherProvider(ABC):
    name: str = "base"

    @abstractmethod
    def plan(self, task: str, context: str) -> TeacherPlan: ...
