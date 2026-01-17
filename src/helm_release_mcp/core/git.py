"""Git operations service using GitPython."""

import logging
from pathlib import Path
from typing import Any

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Exception raised for git operation failures."""

    pass


class GitService:
    """Service for local git operations.

    Wraps GitPython to provide a clean interface for common git operations.
    """

    def clone(
        self,
        url: str,
        target_dir: Path,
        *,
        depth: int | None = None,
        branch: str | None = None,
    ) -> Repo:
        """Clone a repository.

        Args:
            url: Repository URL (HTTPS or SSH).
            target_dir: Local directory to clone into.
            depth: Shallow clone depth (None for full clone).
            branch: Specific branch to clone.

        Returns:
            The cloned repository object.

        Raises:
            GitError: If clone fails.
        """
        try:
            kwargs: dict[str, Any] = {}
            if depth is not None:
                kwargs["depth"] = depth
            if branch is not None:
                kwargs["branch"] = branch

            logger.info(f"Cloning {url} to {target_dir}")
            repo = Repo.clone_from(url, target_dir, **kwargs)
            return repo
        except GitCommandError as e:
            raise GitError(f"Failed to clone {url}: {e}") from e

    def open(self, path: Path) -> Repo:
        """Open an existing repository.

        Args:
            path: Path to the repository.

        Returns:
            The repository object.

        Raises:
            GitError: If not a valid git repository.
        """
        try:
            return Repo(path)
        except InvalidGitRepositoryError as e:
            raise GitError(f"Not a valid git repository: {path}") from e

    def pull(self, repo: Repo, *, remote: str = "origin", branch: str | None = None) -> None:
        """Pull latest changes from remote.

        Args:
            repo: Repository object.
            remote: Remote name.
            branch: Branch to pull (default: current branch).

        Raises:
            GitError: If pull fails.
        """
        try:
            remote_obj = repo.remote(remote)
            if branch:
                remote_obj.pull(branch)
            else:
                remote_obj.pull()
            logger.info(f"Pulled latest changes from {remote}")
        except GitCommandError as e:
            raise GitError(f"Failed to pull from {remote}: {e}") from e

    def fetch(self, repo: Repo, *, remote: str = "origin") -> None:
        """Fetch updates from remote without merging.

        Args:
            repo: Repository object.
            remote: Remote name.
        """
        try:
            repo.remote(remote).fetch()
        except GitCommandError as e:
            raise GitError(f"Failed to fetch from {remote}: {e}") from e

    def checkout(
        self,
        repo: Repo,
        branch: str,
        *,
        create: bool = False,
        start_point: str | None = None,
    ) -> None:
        """Checkout a branch.

        Args:
            repo: Repository object.
            branch: Branch name.
            create: Create the branch if it doesn't exist.
            start_point: Starting point for new branch (e.g., "origin/main").

        Raises:
            GitError: If checkout fails.
        """
        try:
            if create:
                if start_point:
                    repo.git.checkout("-b", branch, start_point)
                else:
                    repo.git.checkout("-b", branch)
                logger.info(f"Created and checked out branch: {branch}")
            else:
                repo.git.checkout(branch)
                logger.info(f"Checked out branch: {branch}")
        except GitCommandError as e:
            raise GitError(f"Failed to checkout {branch}: {e}") from e

    def create_branch(
        self,
        repo: Repo,
        branch: str,
        *,
        start_point: str = "origin/main",
        checkout: bool = True,
    ) -> None:
        """Create a new branch.

        Args:
            repo: Repository object.
            branch: Branch name to create.
            start_point: Starting point for the branch.
            checkout: Whether to checkout the branch after creating.

        Raises:
            GitError: If branch creation fails.
        """
        self.fetch(repo)
        self.checkout(repo, branch, create=True, start_point=start_point)

    def commit(
        self,
        repo: Repo,
        message: str,
        *,
        files: list[str] | None = None,
        all_changes: bool = False,
    ) -> str:
        """Create a commit.

        Args:
            repo: Repository object.
            message: Commit message.
            files: Specific files to commit (default: all staged).
            all_changes: Stage all changes before committing.

        Returns:
            The commit SHA.

        Raises:
            GitError: If commit fails.
        """
        try:
            if files:
                repo.index.add(files)
            elif all_changes:
                repo.git.add("-A")

            commit = repo.index.commit(message)
            logger.info(f"Created commit: {commit.hexsha[:8]} - {message}")
            return commit.hexsha
        except GitCommandError as e:
            raise GitError(f"Failed to commit: {e}") from e

    def push(
        self,
        repo: Repo,
        *,
        remote: str = "origin",
        branch: str | None = None,
        set_upstream: bool = False,
    ) -> None:
        """Push commits to remote.

        Args:
            repo: Repository object.
            remote: Remote name.
            branch: Branch to push (default: current branch).
            set_upstream: Set upstream tracking.

        Raises:
            GitError: If push fails.
        """
        try:
            remote_obj = repo.remote(remote)
            target_branch = branch or repo.active_branch.name

            if set_upstream:
                repo.git.push("--set-upstream", remote, target_branch)
            else:
                remote_obj.push(target_branch)

            logger.info(f"Pushed {target_branch} to {remote}")
        except GitCommandError as e:
            raise GitError(f"Failed to push: {e}") from e

    def get_current_branch(self, repo: Repo) -> str:
        """Get the current branch name.

        Args:
            repo: Repository object.

        Returns:
            Current branch name.
        """
        return repo.active_branch.name

    def get_remote_url(self, repo: Repo, remote: str = "origin") -> str:
        """Get the URL of a remote.

        Args:
            repo: Repository object.
            remote: Remote name.

        Returns:
            Remote URL.
        """
        return repo.remote(remote).url

    def has_changes(self, repo: Repo) -> bool:
        """Check if there are uncommitted changes.

        Args:
            repo: Repository object.

        Returns:
            True if there are changes.
        """
        return repo.is_dirty(untracked_files=True)

    def get_head_sha(self, repo: Repo) -> str:
        """Get the SHA of the HEAD commit.

        Args:
            repo: Repository object.

        Returns:
            HEAD commit SHA.
        """
        return repo.head.commit.hexsha
