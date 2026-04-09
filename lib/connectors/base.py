"""DriveConnector ABC and related types for Athanor Phase 3 RAG."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List, Protocol, runtime_checkable


class ConnectorError(Exception):
    """Base exception for connector errors."""


@dataclass
class ProjectInfo:
    """Information about a Proton Drive project discovered via marker file."""

    name: str
    description: str = ""
    graph_enabled: bool = False
    feeds_into: List[str] = field(default_factory=list)
    system_prompt_hint: str = ""
    exclude: List[str] = field(default_factory=list)


@runtime_checkable
class DriveConnector(Protocol):
    """Interface for accessing Proton Drive projects."""

    @abc.abstractmethod
    def list_projects(self) -> List[ProjectInfo]:
        """List all projects discovered from marker files.

        Returns:
            List of ProjectInfo objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def download(self, project_name: str, dest_dir: str) -> None:
        """Download a project's files to a temporary directory.

        Args:
            project_name: The project name (from marker file suffix).
            dest_dir: Absolute path to directory where files should be downloaded.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def upload_checkpoint(self, project_name: str, checkpoint_content: str) -> None:
        """Upload a checkpoint file for the project.

        Args:
            project_name: The project name.
            checkpoint_content: The content of the checkpoint.md file.
        """
        raise NotImplementedError