"""Connector factory for Athanor Phase 3 RAG."""

from .base import DriveConnector, ProjectInfo, ConnectorError


def get_connector(connector_type: str) -> DriveConnector:
    """Factory function to get a connector instance.

    Args:
        connector_type: Type of connector to create. Currently only "proton" is supported.

    Returns:
        An instance of a DriveConnector implementation.

    Raises:
        ValueError: If an unsupported connector type is requested.
    """
    if connector_type == "proton":
        # Import here to avoid circular imports and allow for optional dependencies
        from .proton import ProtonDriveConnector
        return ProtonDriveConnector()
    else:
        raise ValueError(f"Unsupported connector type: {connector_type}")