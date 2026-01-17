"""Global MCP tools for discovery and status queries."""

import asyncio
import logging
from dataclasses import asdict
from typing import Any

from mcp.server.fastmcp import FastMCP

from helm_release_mcp.repos.registry import RepoRegistry

logger = logging.getLogger(__name__)


def register_global_tools(mcp: FastMCP, registry: RepoRegistry) -> None:
    """Register global discovery and status tools.

    Args:
        mcp: FastMCP server instance.
        registry: Repository registry.
    """

    # =========================================================================
    # Discovery Tools
    # =========================================================================

    @mcp.tool()
    async def list_repos() -> dict[str, Any]:
        """List all managed repositories with their types and available operations.

        Returns information about each configured repository including
        its name, type, description, and available operations.
        """
        repos_info = []

        for name in registry.list_repos():
            repo = registry.get_repo(name)
            if repo:
                operations = repo.get_operations()
                repos_info.append(
                    {
                        "name": repo.name,
                        "github": repo.github_path,
                        "type": repo.repo_type,
                        "description": repo.config.description,
                        "operations": list(operations.keys()),
                    }
                )

        return {
            "repos": repos_info,
            "count": len(repos_info),
        }

    @mcp.tool()
    async def get_repo_status(repo: str) -> dict[str, Any]:
        """Get high-level status of a specific repository.

        Args:
            repo: Repository name.

        Returns status including latest release, open PRs, running workflows.
        """
        repo_obj = registry.get_repo(repo)
        if not repo_obj:
            return {
                "success": False,
                "error": f"Repository not found: {repo}",
            }

        try:
            status = await repo_obj.get_status()
            return {
                "success": True,
                **asdict(status),
            }
        except Exception as e:
            logger.exception(f"Error getting status for {repo}")
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def get_repo_operations(repo: str) -> dict[str, Any]:
        """Get available operations for a repository.

        Args:
            repo: Repository name.

        Returns list of operations with their parameters and descriptions.
        """
        repo_obj = registry.get_repo(repo)
        if not repo_obj:
            return {
                "success": False,
                "error": f"Repository not found: {repo}",
            }

        operations = repo_obj.get_operations()

        return {
            "success": True,
            "repo": repo,
            "type": repo_obj.repo_type,
            "operations": {name: asdict(info) for name, info in operations.items()},
        }

    # =========================================================================
    # Status Query Tools
    # =========================================================================

    @mcp.tool()
    async def check_workflow(repo: str, run_id: int) -> dict[str, Any]:
        """Check the status of a GitHub Actions workflow run.

        Args:
            repo: Repository name.
            run_id: Workflow run ID.

        Returns workflow status including conclusion if completed.
        """
        repo_obj = registry.get_repo(repo)
        if not repo_obj:
            return {
                "success": False,
                "error": f"Repository not found: {repo}",
            }

        try:
            run_info = registry.services.github.get_workflow_run(repo_obj.github_path, run_id)
            return {
                "success": True,
                "id": run_info.id,
                "name": run_info.name,
                "status": run_info.status,
                "conclusion": run_info.conclusion,
                "html_url": run_info.html_url,
                "head_branch": run_info.head_branch,
                "event": run_info.event,
                "created_at": run_info.created_at.isoformat(),
                "updated_at": run_info.updated_at.isoformat(),
            }
        except Exception as e:
            logger.exception(f"Error checking workflow {run_id}")
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def check_pr(repo: str, pr_number: int) -> dict[str, Any]:
        """Check the status of a pull request.

        Args:
            repo: Repository name.
            pr_number: Pull request number.

        Returns PR status including state, checks, and review status.
        """
        repo_obj = registry.get_repo(repo)
        if not repo_obj:
            return {
                "success": False,
                "error": f"Repository not found: {repo}",
            }

        try:
            github_path = repo_obj.github_path
            github = registry.services.github

            # Get PR info
            pr_info = github.get_pr(github_path, pr_number)

            # Get checks status
            checks = github.get_pr_checks_status(github_path, pr_number)

            # Get reviews
            reviews = github.get_pr_reviews(github_path, pr_number)

            # Determine overall review state
            review_state = "pending"
            for review in reversed(reviews):
                if review["state"] in ("APPROVED", "CHANGES_REQUESTED"):
                    review_state = review["state"].lower()
                    break

            return {
                "success": True,
                "number": pr_info.number,
                "title": pr_info.title,
                "state": pr_info.state,
                "draft": pr_info.draft,
                "mergeable": pr_info.mergeable,
                "merged": pr_info.merged,
                "html_url": pr_info.html_url,
                "head_ref": pr_info.head_ref,
                "base_ref": pr_info.base_ref,
                "checks_state": checks["state"],
                "checks_passed": checks["state"] == "success",
                "review_state": review_state,
                "reviews_count": len(reviews),
                "created_at": pr_info.created_at.isoformat(),
                "updated_at": pr_info.updated_at.isoformat(),
            }
        except Exception as e:
            logger.exception(f"Error checking PR #{pr_number}")
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def wait_for_workflow(
        repo: str,
        run_id: int,
        timeout: int = 3600,
        poll_interval: int = 10,
    ) -> dict[str, Any]:
        """Wait for a workflow run to complete.

        Args:
            repo: Repository name.
            run_id: Workflow run ID.
            timeout: Maximum seconds to wait (default: 3600).
            poll_interval: Seconds between status checks (default: 10).

        Returns final workflow status when completed or timeout.
        """
        repo_obj = registry.get_repo(repo)
        if not repo_obj:
            return {
                "success": False,
                "error": f"Repository not found: {repo}",
            }

        github = registry.services.github
        github_path = repo_obj.github_path

        elapsed = 0
        last_status = None

        while elapsed < timeout:
            try:
                run_info = github.get_workflow_run(github_path, run_id)
                last_status = run_info.status

                if run_info.status == "completed":
                    return {
                        "success": True,
                        "completed": True,
                        "id": run_info.id,
                        "name": run_info.name,
                        "status": run_info.status,
                        "conclusion": run_info.conclusion,
                        "html_url": run_info.html_url,
                        "elapsed_seconds": elapsed,
                    }

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            except Exception as e:
                logger.warning(f"Error polling workflow {run_id}: {e}")
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        return {
            "success": False,
            "completed": False,
            "error": "Timeout waiting for workflow completion",
            "timeout": timeout,
            "last_status": last_status,
        }

    @mcp.tool()
    async def list_workflow_runs(
        repo: str,
        workflow_file: str | None = None,
        branch: str | None = None,
        status: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """List recent workflow runs for a repository.

        Args:
            repo: Repository name.
            workflow_file: Filter by workflow file (e.g., "ci.yaml").
            branch: Filter by branch.
            status: Filter by status (queued, in_progress, completed).
            limit: Maximum runs to return (default: 10).
        """
        repo_obj = registry.get_repo(repo)
        if not repo_obj:
            return {
                "success": False,
                "error": f"Repository not found: {repo}",
            }

        try:
            runs = registry.services.github.list_workflow_runs(
                repo_obj.github_path,
                workflow_file=workflow_file,
                branch=branch,
                status=status,
                limit=limit,
            )

            return {
                "success": True,
                "runs": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "status": r.status,
                        "conclusion": r.conclusion,
                        "html_url": r.html_url,
                        "head_branch": r.head_branch,
                        "event": r.event,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in runs
                ],
                "count": len(runs),
            }
        except Exception as e:
            logger.exception("Error listing workflow runs")
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def list_open_prs(repo: str, base: str | None = None) -> dict[str, Any]:
        """List open pull requests for a repository.

        Args:
            repo: Repository name.
            base: Filter by base branch.
        """
        repo_obj = registry.get_repo(repo)
        if not repo_obj:
            return {
                "success": False,
                "error": f"Repository not found: {repo}",
            }

        try:
            prs = registry.services.github.list_open_prs(repo_obj.github_path, base=base)

            return {
                "success": True,
                "prs": [
                    {
                        "number": pr.number,
                        "title": pr.title,
                        "state": pr.state,
                        "draft": pr.draft,
                        "html_url": pr.html_url,
                        "head_ref": pr.head_ref,
                        "base_ref": pr.base_ref,
                        "created_at": pr.created_at.isoformat(),
                    }
                    for pr in prs
                ],
                "count": len(prs),
            }
        except Exception as e:
            logger.exception("Error listing open PRs")
            return {
                "success": False,
                "error": str(e),
            }
