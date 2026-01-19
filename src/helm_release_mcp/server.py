"""FastMCP server setup and configuration."""

import hmac
import logging
from pathlib import Path

from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp import FastMCP

from helm_release_mcp.repos.registry import RepoRegistry
from helm_release_mcp.settings import get_settings
from helm_release_mcp.tools.global_tools import register_global_tools
from helm_release_mcp.tools.repo_tools import register_repo_tools

logger = logging.getLogger(__name__)


class StaticTokenVerifier(TokenVerifier):
    def __init__(self, token: str, base_url: str | None = None) -> None:
        super().__init__(base_url=base_url)
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(token, self._token):
            return AccessToken(token=token, client_id="static", scopes=[], expires_at=None)
        return None


def create_server() -> FastMCP:
    """Create and configure the MCP server.

    Returns:
        Configured FastMCP server instance.
    """
    # Load settings
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create registry from config
    config_path = Path(settings.config_path)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    logger.info(f"Loading config from: {config_path}")
    logger.info(f"Workspace directory: {settings.workspace_dir}")

    registry = RepoRegistry.from_config(
        config_path,
        github_token=settings.github_token,
        workspace_dir=settings.workspace_dir,
        github_api_base_url=settings.github_api_base_url,
    )

    token_verifier: StaticTokenVerifier | None = None
    if settings.auth_token:
        token_verifier = StaticTokenVerifier(settings.auth_token)

    # Create FastMCP server
    mcp = FastMCP(
        "Helm Release MCP",
        instructions="""
        This MCP server manages Helm release workflows for configured repositories.

        Discovery:
        - Use MCP `list_tools` for the authoritative tool list and schemas.
        - Use `list_repos` to see configured repositories.
        - Use `get_repo_operations` to learn per-repo actions.

        Common flow:
        1. Discover repositories and operations.
        2. Trigger repo-specific workflows.
        3. Track workflow runs with `check_workflow` or `wait_for_workflow`.
        """,
        auth=token_verifier,
        host=settings.host,
        port=settings.port,
    )

    # Register global tools
    register_global_tools(mcp, registry)

    # Register repository-specific tools
    register_repo_tools(mcp, registry)

    logger.info(f"Server initialized with {len(registry.list_repos())} repositories")

    return mcp
