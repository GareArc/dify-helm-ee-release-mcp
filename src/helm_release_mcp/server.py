"""FastMCP server setup and configuration."""

import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from helm_release_mcp.repos.registry import RepoRegistry
from helm_release_mcp.settings import get_settings
from helm_release_mcp.tools.global_tools import register_global_tools
from helm_release_mcp.tools.repo_tools import register_repo_tools

logger = logging.getLogger(__name__)


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

    # Create FastMCP server
    mcp = FastMCP(
        "Helm Release MCP",
        instructions="""
        This MCP server helps manage Helm chart releases across GitHub repositories.

        ## Available Tools

        ### Discovery
        - `list_repos`: List all managed repositories
        - `get_repo_status`: Get status of a specific repository
        - `get_repo_operations`: Get available operations for a repository

        ### Status Queries
        - `check_workflow`: Check status of a GitHub Actions workflow run
        - `check_pr`: Check status of a pull request
        - `wait_for_workflow`: Wait for a workflow to complete
        - `list_workflow_runs`: List recent workflow runs
        - `list_open_prs`: List open pull requests

        ### Repository Operations
        Tools are named `{repo_name}__{operation}` where repo_name is from your config.

        For dify-helm repos:
        - `{repo}__list_charts`: List all charts
        - `{repo}__get_chart_info`: Get chart details
        - `{repo}__prepare_release`: Create release PR
        - `{repo}__publish_release`: Merge PR and create release
        - `{repo}__lint_chart`: Validate a chart

        For dify-enterprise repos:
        - `{repo}__get_version`: Get current version
        - `{repo}__bump_version`: Bump version
        - `{repo}__prepare_release`: Create release PR
        - `{repo}__trigger_build`: Trigger CI workflow
        - `{repo}__publish_release`: Merge PR and create release
        - `{repo}__update_helm_chart`: Update associated Helm chart

        ## Typical Workflow

        1. `list_repos()` - See available repositories
        2. `{repo}__prepare_release(...)` - Create a release PR
        3. `check_pr(repo, pr_number)` - Monitor PR status
        4. After approval: `{repo}__publish_release(...)` - Merge and release
        5. `check_workflow(repo, run_id)` - Monitor publish workflow
        """,
    )

    # Register global tools
    register_global_tools(mcp, registry)

    # Register repository-specific tools
    register_repo_tools(mcp, registry)

    logger.info(f"Server initialized with {len(registry.list_repos())} repositories")

    return mcp
