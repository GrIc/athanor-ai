"""Connector factory for Athanor Phase 3 RAG."""

import os
from .base import DriveConnector, ProjectInfo, ConnectorError


def get_connector(connector_type: str | None = None, **kwargs) -> DriveConnector:
    """Factory function to get a connector instance.

    Args:
        connector_type: Type of connector to create. Defaults to CONNECTOR_TYPE env var or "proton".

    Returns:
        An instance of a DriveConnector implementation.

    Raises:
        ValueError: If an unsupported connector type is requested.
    """
    ctype = connector_type or os.environ.get("CONNECTOR_TYPE", "proton")
    if ctype == "proton":
        # Import here to avoid circular imports and allow for optional dependencies
        from .proton import ProtonDriveConnector
        return ProtonDriveConnector(**kwargs)
    else:
        raise ValueError(f"Unsupported connector type: {ctype}")