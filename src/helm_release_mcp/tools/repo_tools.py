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
    if repo.repo_type == "dify":
        _register_dify_tools(mcp, repo)
    elif repo.repo_type == "dify-helm":
        _register_dify_helm_tools(mcp, repo)
    elif repo.repo_type == "dify-enterprise":
        _register_dify_enterprise_tools(mcp, repo)
    elif repo.repo_type == "dify-enterprise-frontend":
        _register_dify_enterprise_frontend_tools(mcp, repo)


def _register_dify_tools(mcp: FastMCP, repo: BaseRepo) -> None:
    """Register tools for a dify repository."""

    @mcp.tool(name=f"{repo.name}__create_release_branch")
    async def create_release_branch(
        base_ref: str,
        branch_name: str,
    ) -> dict[str, Any]:
        """Create a new release branch based on a specific ref.

        Args:
            base_ref: Git ref to base the branch on (tag, branch, or SHA, e.g., "0.15.3", "main").
            branch_name: Name for the new release branch (e.g., "release/ee-1.0.0").
        """
        method = repo.get_operation_method("create_release_branch")
        if method:
            return await method(base_ref, branch_name)
        return {"success": False, "error": "Operation not found"}


def _register_dify_helm_tools(mcp: FastMCP, repo: BaseRepo) -> None:
    """Register tools for a dify-helm repository."""

    @mcp.tool(name=f"{repo.name}__trigger_cve_scan")
    async def trigger_cve_scan(branch: str) -> dict[str, Any]:
        """Trigger container security scan workflow on a release branch.

        Args:
            branch: Release branch name (e.g., "release/1.0.0").
        """
        method = repo.get_operation_method("trigger_cve_scan")
        if method:
            return await method(branch)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__trigger_benchmark")
    async def trigger_benchmark(branch: str) -> dict[str, Any]:
        """Trigger benchmark test workflow on a release branch.

        Args:
            branch: Release branch name (e.g., "release/1.0.0").
        """
        method = repo.get_operation_method("trigger_benchmark")
        if method:
            return await method(branch)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__trigger_license_review")
    async def trigger_license_review(branch: str) -> dict[str, Any]:
        """Trigger dependency license review workflow on a release branch.

        Args:
            branch: Release branch name (e.g., "release/1.0.0").
        """
        method = repo.get_operation_method("trigger_license_review")
        if method:
            return await method(branch)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__trigger_linear_checklist")
    async def trigger_linear_checklist(branch: str) -> dict[str, Any]:
        """Trigger Linear release checklist workflow on a release branch.

        Args:
            branch: Release branch name (e.g., "release/1.0.0").
        """
        method = repo.get_operation_method("trigger_linear_checklist")
        if method:
            return await method(branch)
        return {"success": False, "error": "Operation not found"}

    @mcp.tool(name=f"{repo.name}__release")
    async def release(branch: str) -> dict[str, Any]:
        """Trigger release workflow to publish Helm chart to gh-pages.

        Args:
            branch: Release branch name (e.g., "release/1.0.0").
        """
        method = repo.get_operation_method("release")
        if method:
            return await method(branch)
        return {"success": False, "error": "Operation not found"}


def _register_dify_enterprise_tools(mcp: FastMCP, repo: BaseRepo) -> None:
    """Register tools for a dify-enterprise repository."""

    @mcp.tool(name=f"{repo.name}__create_tag")
    async def create_tag(
        branch: str,
        tag: str,
    ) -> dict[str, Any]:
        """Create a tag on a branch to trigger build/CI workflow.

        Args:
            branch: Branch name to create the tag on (e.g., "release/1.0.0").
            tag: Tag name (e.g., "v1.0.0").
        """
        method = repo.get_operation_method("create_tag")
        if method:
            return await method(branch, tag)
        return {"success": False, "error": "Operation not found"}


def _register_dify_enterprise_frontend_tools(mcp: FastMCP, repo: BaseRepo) -> None:
    """Register tools for a dify-enterprise-frontend repository."""

    @mcp.tool(name=f"{repo.name}__create_tag")
    async def create_tag(
        branch: str,
        tag: str,
    ) -> dict[str, Any]:
        """Create a tag on a branch to trigger build/CI workflow.

        Args:
            branch: Branch name to create the tag on (e.g., "release/1.0.0").
            tag: Tag name (e.g., "v1.0.0").
        """
        method = repo.get_operation_method("create_tag")
        if method:
            return await method(branch, tag)
        return {"success": False, "error": "Operation not found"}
