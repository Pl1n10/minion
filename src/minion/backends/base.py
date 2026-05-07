"""Backend interface for repository mapping providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileEntry:
    """A single file known to the backend."""

    path: Path
    size: int
    language: str | None = None

    @property
    def relpath(self) -> str:
        return str(self.path)


@dataclass
class BackendStatus:
    name: str
    available: bool
    detail: str = ""
    version: str | None = None


class RepoBackend(ABC):
    """Abstract repo-mapping backend.

    Implementations may use the local filesystem, an external tool like
    Repowise, or any future indexing service. The MVP only needs file
    enumeration; richer queries (symbol graphs, embeddings) can be added
    via subclassing later.
    """

    name: str = "base"

    @abstractmethod
    def status(self) -> BackendStatus: ...

    @abstractmethod
    def list_files(self) -> list[FileEntry]: ...

    def search(self, query: str, limit: int = 50) -> list[FileEntry]:
        """Default: filename substring match. Override for smarter backends."""
        q = query.lower()
        return [f for f in self.list_files() if q in f.relpath.lower()][:limit]
