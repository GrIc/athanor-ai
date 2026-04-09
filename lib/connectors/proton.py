"""ProtonDriveConnector - to be implemented in Step 8."""

from typing import List
from .base import DriveConnector, ProjectInfo, ConnectorError


class ProtonDriveConnector(DriveConnector):
    """Placeholder for Proton Drive connector using rclone subprocess.

    This will be implemented in Step 8.
    """

    def list_projects(self) -> List[ProjectInfo]:
        raise NotImplementedError("ProtonDriveConnector not yet implemented")

    def download(self, project_name: str, dest_dir: str) -> None:
        raise NotImplementedError("ProtonDriveConnector not yet implemented")

    def upload_checkpoint(self, project_name: str, checkpoint_content: str) -> None:
        raise NotImplementedError("ProtonDriveConnector not yet implemented")