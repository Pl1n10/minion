"""Teacher providers."""

from __future__ import annotations

from ..config import MinionConfig
from .base import TeacherPlan, TeacherProvider
from .noop import NoopTeacher

__all__ = ["TeacherPlan", "TeacherProvider", "NoopTeacher", "select_teacher"]


def select_teacher(cfg: MinionConfig) -> TeacherProvider:
    if cfg.teacher.provider == "noop":
        return NoopTeacher()
    return NoopTeacher()
