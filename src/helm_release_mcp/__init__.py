"""Helm Release MCP Server - Automate Helm chart releases across GitHub repositories."""

from helm_release_mcp.server import create_server
from helm_release_mcp.settings import get_settings


def main() -> None:
    """Entry point for the MCP server."""
    settings = get_settings()
    server = create_server()
    server.run(settings.transport)


__all__ = ["main", "create_server"]
