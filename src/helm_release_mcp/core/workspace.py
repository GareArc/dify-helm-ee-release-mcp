"""Workspace manager for local repository clones."""

import logging
import shutil
from pathlib import Path

from git import Repo

from helm_release_mcp.core.git import GitError, GitService

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages local clones of repositories.

    Provides methods to ensure repositories are available locally,
    with automatic cloning and updating.
    """

    def __init__(self, workspace_dir: Path, git_service: GitService, github_token: str) -> None:
        """Initialize the workspace manager.

        Args:
            workspace_dir: Base directory for repository clones.
            git_service: Git service instance.
            github_token: GitHub token for authentication.
        """
        self._workspace_dir = workspace_dir
        self._git = git_service
        self._token = github_token
        self._repos: dict[str, Repo] = {}

        # Ensure workspace directory exists
        self._workspace_dir.mkdir(parents=True, exist_ok=True)

    def get_repo_path(self, repo_name: str) -> Path:
        """Get the local path for a repository.

        Args:
            repo_name: Repository name (used as directory name).

        Returns:
            Path to the local repository.
        """
        return self._workspace_dir / repo_name

    def ensure_repo(
        self,
        repo_name: str,
        github_path: str,
        *,
        branch: str = "main",
        force_fresh: bool = False,
        token: str | None = None,
    ) -> Repo:
        """Ensure a repository is available locally and up to date.

        If the repository doesn't exist, it will be cloned.
        If it exists, it will be updated with the latest changes.

        Args:
            repo_name: Local name for the repository.
            github_path: GitHub path in "owner/repo" format.
            branch: Default branch to checkout.
            force_fresh: Delete and re-clone the repository.
            token: Optional token override for this repo.

        Returns:
            The repository object.

        Raises:
            GitError: If repository operations fail.
        """
        repo_path = self.get_repo_path(repo_name)
        effective_token = token or self._token

        if force_fresh and repo_path.exists():
            logger.info(f"Force fresh: removing {repo_path}")
            shutil.rmtree(repo_path)
            self._repos.pop(repo_name, None)

        if repo_path.exists() and (repo_path / ".git").exists():
            return self._update_repo(repo_name, repo_path, branch)

        return self._clone_repo(repo_name, github_path, repo_path, branch, effective_token)

    def _clone_repo(
        self,
        repo_name: str,
        github_path: str,
        repo_path: Path,
        branch: str,
        token: str,
    ) -> Repo:
        """Clone a repository."""
        url = self._get_authenticated_url(github_path, token)

        logger.info(f"Cloning {github_path} to {repo_path}")
        repo = self._git.clone(url, repo_path, branch=branch)
        self._repos[repo_name] = repo
        return repo

    def _update_repo(self, repo_name: str, repo_path: Path, branch: str) -> Repo:
        """Update an existing repository."""
        if repo_name in self._repos:
            repo = self._repos[repo_name]
        else:
            repo = self._git.open(repo_path)
            self._repos[repo_name] = repo

        try:
            # Fetch latest
            self._git.fetch(repo)

            # Checkout and pull default branch
            current_branch = self._git.get_current_branch(repo)
            if current_branch != branch:
                # Stash any changes if needed
                if self._git.has_changes(repo):
                    logger.warning(f"Repo {repo_name} has uncommitted changes")
                self._git.checkout(repo, branch)

            self._git.pull(repo, branch=branch)
            logger.info(f"Updated {repo_name} to latest {branch}")
        except GitError as e:
            logger.warning(f"Failed to update {repo_name}: {e}")
            # Return the repo anyway - it may still be usable

        return repo

    def get_repo(self, repo_name: str) -> Repo | None:
        """Get a previously loaded repository.

        Args:
            repo_name: Repository name.

        Returns:
            Repository object if loaded, None otherwise.
        """
        if repo_name in self._repos:
            return self._repos[repo_name]

        repo_path = self.get_repo_path(repo_name)
        if repo_path.exists() and (repo_path / ".git").exists():
            try:
                repo = self._git.open(repo_path)
                self._repos[repo_name] = repo
                return repo
            except GitError:
                return None
        return None

    def prepare_branch(
        self,
        repo_name: str,
        branch_name: str,
        *,
        start_point: str | None = None,
    ) -> Repo:
        """Prepare a new branch for work.

        Creates or checks out a branch, ensuring it's based on the latest
        remote state.

        Args:
            repo_name: Repository name.
            branch_name: Branch to create/checkout.
            start_point: Starting point for new branch (default: origin/main).

        Returns:
            Repository object on the prepared branch.

        Raises:
            GitError: If branch preparation fails.
        """
        repo = self.get_repo(repo_name)
        if not repo:
            raise GitError(f"Repository not found: {repo_name}")

        # Fetch latest
        self._git.fetch(repo)

        # Determine start point
        if not start_point:
            start_point = f"origin/{repo.remotes.origin.refs[0].remote_head}"

        # Create and checkout branch
        self._git.create_branch(repo, branch_name, start_point=start_point)

        return repo

    def cleanup_repo(self, repo_name: str) -> None:
        """Remove a repository from the workspace.

        Args:
            repo_name: Repository name.
        """
        repo_path = self.get_repo_path(repo_name)

        if repo_name in self._repos:
            del self._repos[repo_name]

        if repo_path.exists():
            logger.info(f"Removing {repo_path}")
            shutil.rmtree(repo_path)

    def cleanup_all(self) -> None:
        """Remove all repositories from the workspace."""
        self._repos.clear()

        if self._workspace_dir.exists():
            for item in self._workspace_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)

    def _get_authenticated_url(self, github_path: str, token: str | None = None) -> str:
        """Get an authenticated HTTPS URL for a GitHub repository.

        Args:
            github_path: GitHub path in "owner/repo" format.
            token: Optional token override.

        Returns:
            Authenticated HTTPS URL.
        """
        effective_token = token or self._token
        return f"https://x-access-token:{effective_token}@github.com/{github_path}.git"

    def list_repos(self) -> list[str]:
        """List all repositories in the workspace.

        Returns:
            List of repository names.
        """
        repos = []
        if self._workspace_dir.exists():
            for item in self._workspace_dir.iterdir():
                if item.is_dir() and (item / ".git").exists():
                    repos.append(item.name)
        return repos
