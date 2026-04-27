import subprocess
import shutil
import yaml
import tempfile
import logging
from pathlib import Path
from collections import defaultdict
from typing import Optional

from lib.connectors.base import DriveConnector, ProjectInfo, ConnectorError

logger = logging.getLogger(__name__)

class ProtonDriveConnector(DriveConnector):
    def __init__(self, rclone_conf: str, remote_name: str = "proton",
                 drive_root: str = "/"):
        """
        rclone_conf: path to rclone.conf on disk (e.g. "/tmp/rclone.conf")
        remote_name: rclone remote name as defined in rclone.conf
        drive_root: root path on Proton Drive to scan (default: "/")
        """
        self.rclone_conf = rclone_conf
        self.remote = remote_name
        self.root = drive_root.rstrip("/")
        if not self.root:
            self.root = "/"

    def _rclone(self, args: list[str]) -> subprocess.CompletedProcess:
        cmd = ["rclone", "--config", self.rclone_conf] + args
        logger.debug(f"Running rclone: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ConnectorError(f"rclone failed: {result.stderr}")
        return result

    def list_projects(self) -> list[ProjectInfo]:
        """
        rclone lsf --recursive --include "athanor.*" --exclude ".athanor/**"
        Groups results by project name (suffix after 'athanor.').
        Reads YAML content if marker file is not empty.
        """
        remote_path = f"{self.remote}:{self.root}" if self.root == "/" else f"{self.remote}:{self.root}/"
        args = [
            "lsf",
            "--recursive",
            "--include", "athanor.*",
            "--exclude", ".athanor/**",
            remote_path
        ]

        result = self._rclone(args)
        paths = [p for p in result.stdout.splitlines() if p.strip()]

        # Group paths by project name
        projects_map = defaultdict(list)
        for path_str in paths:
            path = Path(path_str)
            name_parts = path.name.split('.')
            if len(name_parts) >= 2 and name_parts[0] == "athanor":
                project_name = name_parts[1]
                # Keep the directory path
                dir_path = str(path.parent)
                if dir_path == ".":
                    dir_path = ""
                projects_map[project_name].append(dir_path)

        projects = []
        for name, source_paths in projects_map.items():
            config = {}
            # Try to read the marker file to get config
            # We just read the first one we find
            if source_paths:
                first_dir = source_paths[0]
                marker_path = f"{first_dir}/athanor.{name}" if first_dir else f"athanor.{name}"
                cat_args = ["cat", f"{remote_path}{marker_path}"]
                try:
                    cat_result = self._rclone(cat_args)
                    content = cat_result.stdout.strip()
                    if content:
                        parsed = yaml.safe_load(content)
                        if isinstance(parsed, dict):
                            config = parsed
                except ConnectorError as e:
                    logger.warning(f"Could not read config for project {name}: {e}")
                except yaml.YAMLError as e:
                    logger.warning(f"Could not parse YAML for project {name}: {e}")

            projects.append(ProjectInfo(name=name, source_paths=source_paths, config=config))

        return projects

    def download_project_files(self, project: ProjectInfo, dest_path: Path) -> list[Path]:
        """
        For each source_path in project.source_paths:
          rclone copy --exclude ".athanor/**" --exclude "athanor.*" --max-size 50M
        """
        dest_path.mkdir(parents=True, exist_ok=True)
        remote_base = f"{self.remote}:{self.root}" if self.root == "/" else f"{self.remote}:{self.root}/"

        for source_path in project.source_paths:
            remote_dir = f"{remote_base}{source_path}" if source_path else remote_base

            # Note: We copy flat to dest_path for simplicity of the ingest pipeline,
            # or preserve hierarchy if multiple source paths. The spec implies flattening or
            # the ingest logic handles it. Let's copy into subdirectories to avoid collisions.
            target_dir = dest_path / source_path if source_path else dest_path
            target_dir.mkdir(parents=True, exist_ok=True)

            args = [
                "copy",
                remote_dir,
                str(target_dir),
                "--exclude", ".athanor/**",
                "--exclude", "athanor.*",
                "--max-size", "50M"
            ]
            self._rclone(args)

        # Return all downloaded files
        downloaded = []
        for p in dest_path.rglob("*"):
            if p.is_file():
                downloaded.append(p)

        return downloaded

    def delete_temp_files(self, dest_path: Path) -> None:
        shutil.rmtree(dest_path, ignore_errors=True)

    def upload_checkpoint(self, project_name: str, checkpoint_content: str) -> None:
        """Write content to a temp file, then rclone copyto to {source_folder}/.athanor/checkpoint.md"""
        # We need the source_folder, but the spec only gives project_name.
        # We must find the first folder that belongs to this project.
        projects = self.list_projects()
        target_proj = next((p for p in projects if p.name == project_name), None)

        if not target_proj or not target_proj.source_paths:
            logger.warning(f"Could not find project {project_name} to upload checkpoint")
            return

        source_folder = target_proj.source_paths[0]

        remote_base = f"{self.remote}:{self.root}" if self.root == "/" else f"{self.remote}:{self.root}/"
        remote_target = f"{remote_base}{source_folder}/.athanor/checkpoint.md" if source_folder else f"{remote_base}.athanor/checkpoint.md"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as tmp:
            tmp.write(checkpoint_content)
            tmp_path = tmp.name

        try:
            args = ["copyto", tmp_path, remote_target]
            self._rclone(args)
            logger.info(f"Uploaded checkpoint to {remote_target}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def read_checkpoint(self, project_name: str) -> Optional[str]:
        """rclone cat {source_folder}/.athanor/checkpoint.md → return content or None"""
        # We need the source_folder, but the spec only gives project_name.
        # We must find the first folder that belongs to this project.
        projects = self.list_projects()
        target_proj = next((p for p in projects if p.name == project_name), None)

        if not target_proj or not target_proj.source_paths:
            return None

        source_folder = target_proj.source_paths[0]
        remote_base = f"{self.remote}:{self.root}" if self.root == "/" else f"{self.remote}:{self.root}/"
        remote_target = f"{remote_base}{source_folder}/.athanor/checkpoint.md" if source_folder else f"{remote_base}.athanor/checkpoint.md"

        try:
            result = self._rclone(["cat", remote_target])
            return result.stdout.strip()
        except ConnectorError:
            # File might not exist
            return None