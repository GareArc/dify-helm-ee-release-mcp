"""Dynamic repository-specific MCP tool registration."""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from helm_release_mcp.repos.base import BaseRepo
from helm_release_mcp.repos.registry import RepoRegistry

logger = logging.getLogger(__name__)


def register_repo_tools(mcp: FastMCP, registry: RepoRegistry) -> None:
    """Register dynamic repository-specific tools.

    For each repository in the registry, creates tools named
    {repo_name}__{operation_name} that delegate to the repo's methods.

    Args:
        mcp: FastMCP server instance.
        registry: Repository registry.
    """
    for repo_name in registry.list_repos():
        repo = registry.get_repo(repo_name)
        if repo:
            _register_repo_operations(mcp, repo)


def _register_repo_operations(mcp: FastMCP, repo: BaseRepo) -> None:
    """Register all operations for a single repository.

    Args:
        mcp: FastMCP server instance.
        repo: Repository instance.
    """
    operations = repo.get_operations()

    for op_name, op_info in operations.items():
        tool_name = f"{repo.name}__{op_name}"

        # Create the tool function with closure over repo and op_name
        _create_tool(mcp, tool_name, repo, op_name, op_info.description)

        logger.debug(f"Registered tool: {tool_name}")

    logger.info(f"Registered {len(operations)} tools for repo: {repo.name} ({repo.repo_type})")


def _create_tool(
    mcp: FastMCP,
    tool_name: str,
    repo: BaseRepo,
    operation_name: str,
    description: str,
) -> None:
    """Create and register a single tool for a repository operation.

    Args:
        mcp: FastMCP server instance.
        tool_name: Full tool name ({repo}__{operation}).
        repo: Repository instance.
        operation_name: Operation method name.
        description: Operation description for the tool.
    """
    # Get the operation method
    method = repo.get_operation_method(operation_name)
    if method is None:
        logger.warning(f"Method not found for operation: {operation_name}")
        return

    # Create wrapper that accepts kwargs and calls the method
    async def tool_wrapper(**kwargs: Any) -> dict[str, Any]:
        """Dynamic tool wrapper."""
        try:
            result = await method(**kwargs)
            return result
        except Exception as e:
            logger.exception(f"Error in {tool_name}")
            return {
                "success": False,
                "error": str(e),
            }

    # Set function metadata for MCP
    tool_wrapper.__name__ = tool_name
    tool_wrapper.__doc__ = f"{description}\n\nRepository: {repo.name} ({repo.github_path})"

    # Register the tool
    # Note: FastMCP will use the function signature to determine parameters
    # Since we use **kwargs, we need to provide parameter info differently
    mcp.tool(name=tool_name, description=tool_wrapper.__doc__)(tool_wrapper)


def register_typed_repo_tools(mcp: FastMCP, registry: RepoRegistry) -> None:
    """Register repository tools with explicit type signatures.

    This alternative registration method creates properly typed tools
    based on the repo type rather than using dynamic **kwargs.

    Args:
        mcp: FastMCP server instance.
        registry: Repository registry.
    """
    for repo_name in registry.list_repos():
        repo = registry.get_repo(repo_name)
        if repo:
            _register_typed_tools_for_repo(mcp, repo)


def _register_typed_tools_for_repo(mcp: FastMCP, repo: BaseRepo) -> None:
    """Register typed tools for a specific repository.

    Creates tools with proper parameter signatures based on repo type.
    """
    if repo.repo_type == "helm-registry":
        _register_helm_registry_tools(mcp, repo)
    elif repo.repo_type == "application":
        _register_application_tools(mcp, repo)


def _register_helm_registry_tools(mcp: FastMCP, repo: BaseRepo) -> None:
    """Register tools for a helm-registry repository."""

    @mcp.tool(name=f"{repo.name}__list_charts")
    async def list_charts() -> dict[str, Any]:
        """List all Helm charts in the registry."""
        method = repo.get_operation_method("list_charts")
        if method:
            return await method()
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__get_chart_info")
    async def get_chart_info(chart: str) -> dict[str, Any]:
        """Get detailed information about a specific chart.

        Args:
            chart: Chart name.
        """
        method = repo.get_operation_method("get_chart_info")
        if method:
            return await method(chart)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__prepare_release")
    async def prepare_release(
        chart: str,
        version: str,
        changelog: str | None = None,
        app_version: str | None = None,
    ) -> dict[str, Any]:
        """Prepare a new chart release by bumping version and creating PR.

        Args:
            chart: Chart name.
            version: New version string.
            changelog: Optional changelog entry.
            app_version: Optional appVersion to set.
        """
        method = repo.get_operation_method("prepare_release")
        if method:
            return await method(chart, version, changelog=changelog, app_version=app_version)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__publish_release")
    async def publish_release(
        chart: str,
        pr_number: int,
        merge_method: str = "squash",
    ) -> dict[str, Any]:
        """Publish a chart release by merging PR and creating release.

        Args:
            chart: Chart name.
            pr_number: PR number to merge.
            merge_method: Git merge method (squash, merge, rebase).
        """
        method = repo.get_operation_method("publish_release")
        if method:
            return await method(chart, pr_number, merge_method=merge_method)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__lint_chart")
    async def lint_chart(chart: str) -> dict[str, Any]:
        """Lint a Helm chart for errors.

        Args:
            chart: Chart name.
        """
        method = repo.get_operation_method("lint_chart")
        if method:
            return await method(chart)
        return {"success": False, "error": "Operation not found"}


def _register_application_tools(mcp: FastMCP, repo: BaseRepo) -> None:
    """Register tools for an application repository."""

    @mcp.tool(name=f"{repo.name}__get_version")
    async def get_version() -> dict[str, Any]:
        """Get the current application version."""
        method = repo.get_operation_method("get_version")
        if method:
            return await method()
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__bump_version")
    async def bump_version(
        bump_type: str = "patch",
        new_version: str | None = None,
    ) -> dict[str, Any]:
        """Bump the application version.

        Args:
            bump_type: Type of bump (major, minor, patch).
            new_version: Explicit version to set (overrides bump_type).
        """
        method = repo.get_operation_method("bump_version")
        if method:
            return await method(bump_type, new_version=new_version)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__prepare_release")
    async def prepare_release(
        version: str,
        changelog: str | None = None,
    ) -> dict[str, Any]:
        """Prepare a new application release.

        Args:
            version: New version string.
            changelog: Optional changelog entry.
        """
        method = repo.get_operation_method("prepare_release")
        if method:
            return await method(version, changelog=changelog)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__trigger_build")
    async def trigger_build(ref: str | None = None) -> dict[str, Any]:
        """Trigger a build/CI workflow.

        Args:
            ref: Git ref to build (default: default branch).
        """
        method = repo.get_operation_method("trigger_build")
        if method:
            return await method(ref=ref)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__publish_release")
    async def publish_release(
        pr_number: int,
        merge_method: str = "squash",
    ) -> dict[str, Any]:
        """Publish a release by merging PR and creating GitHub release.

        Args:
            pr_number: PR number to merge.
            merge_method: Git merge method.
        """
        method = repo.get_operation_method("publish_release")
        if method:
            return await method(pr_number, merge_method=merge_method)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__update_helm_chart")
    async def update_helm_chart(version: str | None = None) -> dict[str, Any]:
        """Update the associated Helm chart with the new app version.

        Args:
            version: Version to set (default: current app version).
        """
        method = repo.get_operation_method("update_helm_chart")
        if method:
            return await method(version)
        return {"success": False, "error": "Operation not found"}
