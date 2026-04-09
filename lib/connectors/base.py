"""DriveConnector ABC and related types for Athanor Phase 3 RAG."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Protocol, runtime_checkable


class ConnectorError(Exception):
    """Base exception for connector errors."""


@dataclass
class ProjectInfo:
    """Information about a Proton Drive project discovered via marker file."""

    name: str
    source_paths: List[str] = field(default_factory=list)
    description: str = ""
    graph_enabled: bool = False
    feeds_into: List[str] = field(default_factory=list)
    system_prompt_hint: str = ""
    exclude: List[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)


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
    def download_project_files(self, project: ProjectInfo, dest_path: Path) -> List[Path]:
        """Download a project's files to a temporary directory.

        Args:
            project: The project info.
            dest_path: Absolute path to directory where files should be downloaded.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_temp_files(self, dest_path: Path) -> None:
        """Delete temporary files."""
        raise NotImplementedError

    @abc.abstractmethod
    def upload_checkpoint(self, project_name: str, checkpoint_content: str) -> None:
        """Upload a checkpoint file for the project.

        Args:
            project_name: The project name.
            checkpoint_content: The content of the checkpoint.md file.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def read_checkpoint(self, project_name: str) -> str | None:
        """Read checkpoint content for a project."""
        raise NotImplementedError