"""Dynamic repository-specific MCP tool registration."""

import inspect
import keyword
import logging
from typing import Any, get_type_hints

from fastmcp import FastMCP

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

    signature = inspect.signature(method)
    parameters = []
    annotations: dict[str, Any] = {}

    # Get type hints from the original method
    try:
        method_hints = get_type_hints(method, include_extras=True)
    except Exception:
        method_hints = {}

    for name, param in signature.parameters.items():
        if name == "self":
            continue

        safe_name = name
        if keyword.iskeyword(safe_name):
            safe_name = f"{safe_name}_"

        # Copy annotation if available
        if name in method_hints:
            annotations[safe_name] = method_hints[name]
        elif param.annotation != inspect.Parameter.empty:
            annotations[safe_name] = param.annotation

        parameters.append(
            param.replace(
                name=safe_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        )

    async def tool_wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        """Dynamic tool wrapper."""
        try:
            result = await method(*args, **kwargs)
            return result
        except Exception as e:
            logger.exception(f"Error in {tool_name}")
            return {
                "success": False,
                "error": str(e),
            }

    tool_wrapper.__name__ = tool_name
    tool_wrapper.__doc__ = f"{description}\n\nRepository: {repo.name} ({repo.github_path})"
    tool_wrapper.__signature__ = inspect.Signature(parameters=parameters)  # type: ignore[attr-defined]
    tool_wrapper.__annotations__ = annotations.copy()
    tool_wrapper.__annotations__["return"] = dict[str, Any]

    mcp.tool(
        name=tool_name,
        description=tool_wrapper.__doc__,
    )(tool_wrapper)
