"""Tag operations for Dify Enterprise Frontend repo."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helm_release_mcp.repos.types.dify_enterprise_frontend.repo import (
        DifyEnterpriseFrontendRepo,
    )


class TagOperationsMixin:
    """Mixin providing tag operations for DifyEnterpriseFrontendRepo."""

    async def create_tag(
        self: "DifyEnterpriseFrontendRepo",
        branch: str,
        tag: str,
    ) -> dict[str, Any]:
        """Create a tag on a branch to trigger build workflow.

        Args:
            branch: Branch name to tag (e.g., "release/1.0.0").
            tag: Tag name to create (e.g., "v1.0.0").
        """
        try:
            repo = self.github.get_repo(self.github_path)

            try:
                branch_ref = repo.get_branch(branch)
                sha = branch_ref.commit.sha
            except Exception:
                return {
                    "success": False,
                    "error": f"Branch not found: {branch}",
                }

            try:
                repo.get_git_ref(f"tags/{tag}")
                return {
                    "success": False,
                    "error": f"Tag already exists: {tag}",
                }
            except Exception:
                pass

            git_tag = repo.create_git_tag(
                tag=tag,
                message=f"Release {tag}",
                object=sha,
                type="commit",
            )
            repo.create_git_ref(ref=f"refs/tags/{tag}", sha=git_tag.sha)

            return {
                "success": True,
                "tag": tag,
                "branch": branch,
                "sha": sha,
                "url": f"https://github.com/{self.github_path}/releases/tag/{tag}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
