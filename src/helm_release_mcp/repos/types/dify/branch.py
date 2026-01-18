"""Branch operations for Dify repo."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helm_release_mcp.repos.types.dify.repo import DifyRepo


class BranchOperationsMixin:
    """Mixin providing branch operations for DifyRepo."""

    async def create_release_branch(
        self: "DifyRepo",
        base_ref: str,
        branch_name: str,
    ) -> dict[str, Any]:
        """Create a release branch from a specific ref.

        Args:
            base_ref: Git ref to base the branch on (tag, branch, or SHA, e.g., "0.15.3", "main", or a commit SHA).
            branch_name: Name for the new branch (e.g., "release/e-1.0.0").
        """
        try:
            repo = self.github.get_repo(self.github_path)

            # Try to resolve the ref to a SHA
            base_sha = None

            # Try as a tag first
            try:
                ref = repo.get_git_ref(f"tags/{base_ref}")
                base_sha = ref.object.sha
            except Exception:
                pass

            # Try as a branch
            if not base_sha:
                try:
                    branch = repo.get_branch(base_ref)
                    base_sha = branch.commit.sha
                except Exception:
                    pass

            # Try as a commit SHA directly
            if not base_sha:
                try:
                    commit = repo.get_commit(base_ref)
                    base_sha = commit.sha
                except Exception:
                    pass

            if not base_sha:
                return {
                    "success": False,
                    "error": f"Could not resolve ref: {base_ref}",
                }

            # Check if branch already exists
            try:
                repo.get_branch(branch_name)
                return {
                    "success": False,
                    "error": f"Branch already exists: {branch_name}",
                }
            except Exception:
                pass

            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)

            return {
                "success": True,
                "branch": branch_name,
                "base_ref": base_ref,
                "sha": base_sha,
                "url": f"https://github.com/{self.github_path}/tree/{branch_name}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
