"""Dify Enterprise repository type."""

from helm_release_mcp.repos.base import BaseRepo, CoreServices, RepoConfig, RepoStatus
from helm_release_mcp.repos.types.dify_enterprise.tag import TagOperationsMixin


class DifyEnterpriseRepo(
    TagOperationsMixin,
    BaseRepo,
    repo_type="dify-enterprise",
):
    """Repository type for Dify Enterprise monorepo."""

    def __init__(self, config: RepoConfig, services: CoreServices) -> None:
        super().__init__(config, services)

    async def get_status(self) -> RepoStatus:
        latest = self.github.get_latest_release(self.github_path)
        open_prs = self.github.list_open_prs(self.github_path)
        running = self.github.list_workflow_runs(self.github_path, status="in_progress", limit=5)

        return RepoStatus(
            name=self.name,
            github=self.github_path,
            type=self.repo_type,
            description=self.config.description,
            latest_release=latest.tag_name if latest else None,
            open_prs_count=len(open_prs),
            running_workflows_count=len(running),
        )
