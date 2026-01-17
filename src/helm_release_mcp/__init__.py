"""Helm Release MCP Server - Automate Helm chart releases across GitHub repositories."""

from helm_release_mcp.server import create_server


def main() -> None:
    """Entry point for the MCP server."""
    server = create_server()
    server.run()


__all__ = ["main", "create_server"]
