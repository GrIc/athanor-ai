# DriveConnector — Interface & Setup Guide

> How the RAG system connects to document sources. Current implementation: Proton Drive via rclone.

---

## Overview

The `DriveConnector` is an abstract interface (`lib/connectors/base.py`) that decouples the RAG ingestion pipeline from any specific cloud storage provider. The only implemented connector is `ProtonDriveConnector` (via rclone subprocess).

To add a new connector (e.g., Google Drive, local filesystem), implement the ABC and register it in `lib/connectors/__init__.py`.

---

## Marker File Convention

Place a file named `athanor.{project_name}` in any folder on Proton Drive. The connector discovers all such files recursively.

**File name**: `athanor.{project_name}`
- `athanor.finances` → project name: `finances`
- `athanor.immobilier` → project name: `immobilier`
- The suffix becomes the ChromaDB collection name and the OpenWebUI model name.

**File content**: empty (all defaults) or optional YAML:

```yaml
# athanor.finances
description: "Financial documents and tax records"
graph_enabled: true          # false by default — enables NetworkX knowledge graph
feeds_into:
  - immobilier               # chunks from this project also indexed in "immobilier"
system_prompt_hint: "Always cite document names and dates when answering."
exclude:
  - archives-avant-2020/     # subfolders to skip during download
```

All fields are optional. An empty file uses defaults: `graph_enabled=false`, no `feeds_into`, no `exclude`.

**Multiple folders, one project**: Place `athanor.finances` in both `/Finances/2024/` and `/Finances/2025/`. The connector groups all matching folders under the same project name and downloads files from all of them.

---

## Control Points (Checkpoints)

After ingestion and conversation, the system writes a checkpoint file to the source folder:

```
{folder}/.athanor/checkpoint.md
```

This file is:
- **Read at ingest time** → cached to GCS `checkpoints/{project}.md`
- **Read at conversation start** → injected as system context
- **Written at conversation end** → LLM summarizes progress → uploaded back to Drive

The `.athanor/` folder and `athanor.*` marker files are excluded from document ingestion.

---

## DriveConnector ABC

```python
# lib/connectors/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class ProjectInfo:
    name: str                    # project name (marker file suffix)
    source_paths: list[str]      # Drive paths containing this project's files
    config: dict = field(default_factory=dict)  # parsed YAML from marker file

class ConnectorError(Exception):
    pass

class DriveConnector(ABC):
    @abstractmethod
    def list_projects(self) -> list[ProjectInfo]:
        """Scan Drive recursively for athanor.* marker files.
        Returns one ProjectInfo per unique project name.
        Excludes .athanor/** subdirectories.
        """

    @abstractmethod
    def download_project_files(
        self,
        project: ProjectInfo,
        dest_path: Path,
    ) -> list[Path]:
        """Download all project files to dest_path.
        Excludes: .athanor/**, athanor.* marker files, files > 50MB.
        Returns list of downloaded file paths.
        IMPORTANT: caller must call delete_temp_files() in a finally block.
        """

    @abstractmethod
    def delete_temp_files(self, dest_path: Path) -> None:
        """Delete temp directory. Always call in finally block.
        Implementation: shutil.rmtree(dest_path, ignore_errors=True)
        """

    @abstractmethod
    def upload_checkpoint(self, project_name: str, content: str) -> None:
        """Write checkpoint content to {source_folder}/.athanor/checkpoint.md on Drive."""

    @abstractmethod
    def read_checkpoint(self, project_name: str) -> Optional[str]:
        """Read checkpoint from {source_folder}/.athanor/checkpoint.md. Returns None if not found."""
```

---

## get_connector() Factory

```python
# lib/connectors/__init__.py

import os
from .base import DriveConnector

def get_connector(connector_type: str = None, **kwargs) -> DriveConnector:
    """Factory. connector_type defaults to CONNECTOR_TYPE env var."""
    ctype = connector_type or os.environ.get("CONNECTOR_TYPE", "proton")
    if ctype == "proton":
        from .proton import ProtonDriveConnector
        return ProtonDriveConnector(**kwargs)
    raise ValueError(f"Unknown connector type: {ctype}. Only 'proton' is implemented.")
```

---

## ProtonDriveConnector — rclone Setup

### 1. Install rclone (v1.65+)

```bash
# Linux
curl https://rclone.org/install.sh | sudo bash

# Verify Proton Drive backend is available
rclone --version | grep -i proton
```

### 2. Configure Proton Drive remote

```bash
rclone config
# → New remote → name: protondrive
# → Type: protondrive
# → Enter your Proton account credentials (OAuth2 flow)
# → Save
```

The config is written to `~/.config/rclone/rclone.conf`. Copy the `[protondrive]` section.

### 3. Store config in Secret Manager

```bash
# Upload rclone.conf to Secret Manager
gcloud secrets create athanor-rclone-conf \
  --replication-policy=user-managed \
  --locations=europe-west9

gcloud secrets versions add athanor-rclone-conf \
  --data-file=~/.config/rclone/rclone.conf
```

The ingest job reads this secret at startup, writes it to `/tmp/rclone.conf`, and deletes it at the end.

### 4. Test the connection

```bash
# List your Proton Drive root
rclone ls protondrive:/

# Check marker file discovery
rclone ls protondrive:/ --include "athanor.*" --recursive
```

### 5. Environment variables for the ingest job

| Variable | Value | Description |
|---|---|---|
| `CONNECTOR_TYPE` | `proton` | Connector implementation to use |
| `PROTON_DRIVE_ROOT` | `/` | Root path on Proton Drive to scan |
| `RCLONE_CONFIG_SECRET` | `athanor-rclone-conf` | Secret Manager secret name |

---

## Implementing a New Connector

1. Create `lib/connectors/{name}.py` implementing all 5 abstract methods.
2. Add `elif ctype == "{name}"` branch in `get_connector()`.
3. Add `CONNECTOR_TYPE={name}` to the ingest job's Terraform env vars.
4. Test with: `python -c "from lib.connectors.{name} import YourConnector; c = YourConnector(); print(c.list_projects())"`

### Key implementation notes

- `list_projects()`: parse marker file content with `yaml.safe_load()`. Handle `None` (empty file) gracefully — return `{}` as config.
- `download_project_files()`: respect `project.config.get("exclude", [])` subdirs. Skip files > 50 MB (log a warning). Never download `.athanor/` or `athanor.*` files.
- `delete_temp_files()`: use `shutil.rmtree(dest_path, ignore_errors=True)` — never raise in cleanup.
- `upload_checkpoint()`: create `.athanor/` directory on Drive if it doesn't exist. Overwrite `checkpoint.md`.

---

## Privacy Notes

- The ingest job is the **only** component that ever accesses Proton Drive.
- The RAG service (`athanor-rag`) never calls rclone. It reads checkpoints from GCS only.
- Documents are never stored on GCS — only vectordb snapshots and checkpoints.
- rclone.conf (which contains OAuth2 tokens) lives only in Secret Manager and `/tmp/rclone.conf` during the job run.
