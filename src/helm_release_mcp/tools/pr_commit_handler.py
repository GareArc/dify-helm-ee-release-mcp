"""PR and commit handling utilities for parsing and validation."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class PrCommitHandler:
    """Handler for PR and commit operations.

    Provides utilities for:
    - Parsing PR URLs and extracting PR numbers
    - Validating PR identifiers against repository paths
    - Performing branch containment checks
    """

    @staticmethod
    def parse_pr_url(pr_url: str) -> tuple[str | None, int | None]:
        """Parse a GitHub PR URL to extract repo path and PR number.

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

        Returns:
            Tuple of (repo_path, pr_number) or (None, None) if invalid.
        """
        # Match patterns like:
        # https://github.com/owner/repo/pull/123
        # https://github.com/owner/repo/pulls/123
        # github.com/owner/repo/pull/123
        pattern = r"github\.com/([^/]+/[^/]+)/pulls?/(\d+)"
        match = re.search(pattern, pr_url)

        if match:
            repo_path = match.group(1)
            pr_number = int(match.group(2))
            return repo_path, pr_number

        return None, None

    @staticmethod
    def resolve_pr_identifier(
        repo_path: str,
        pr_number: int | None = None,
        pr_url: str | None = None,
    ) -> dict[str, Any]:
        """Resolve PR identifier from pr_number or pr_url.

        Args:
            repo_path: Expected repository path in "owner/repo" format.
            pr_number: Direct PR number.
            pr_url: GitHub PR URL.

        Returns:
            Dictionary with 'success', 'pr_number', and 'error' if failed.
        """
        if not pr_number and not pr_url:
            return {
                "success": False,
                "error": "Either pr_number or pr_url must be provided",
            }

        resolved_number = pr_number

        if pr_url:
            url_repo_path, url_pr_number = PrCommitHandler.parse_pr_url(pr_url)

            if not url_repo_path or not url_pr_number:
                return {
                    "success": False,
                    "error": f"Invalid PR URL format: {pr_url}",
                }

            if url_repo_path != repo_path:
                return {
                    "success": False,
                    "error": f"PR URL repo '{url_repo_path}' does not match expected repo '{repo_path}'",
                }

            resolved_number = url_pr_number

        # If both provided, verify they match
        if pr_number and pr_url:
            _, url_pr_number = PrCommitHandler.parse_pr_url(pr_url)
            if url_pr_number != pr_number:
                return {
                    "success": False,
                    "error": f"PR number {pr_number} does not match URL PR number {url_pr_number}",
                }

        return {
            "success": True,
            "pr_number": resolved_number,
        }

    @staticmethod
    def check_commit_in_branch(
        compare_result: dict[str, Any],
        commit_sha: str,
    ) -> bool:
        """Determine if a commit is in a branch based on comparison result.

        Args:
            compare_result: Result from GitHubService.compare_commits.
            commit_sha: The commit SHA being checked.

        Returns:
            True if commit is in the branch, False otherwise.
        """
        # When comparing commit vs branch:
        # - "identical": commit == branch head -> commit is in branch
        # - "behind": commit is behind branch (ancestor) -> commit is in branch
        # - "ahead": commit is ahead of branch -> commit is NOT in branch
        # - "diverged": commit and branch diverged -> commit is NOT in branch

        status = compare_result.get("status")

        return status in ("identical", "behind")
