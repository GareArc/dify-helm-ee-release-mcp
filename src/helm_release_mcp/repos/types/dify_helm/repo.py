"""Dify Helm repository type."""

from helm_release_mcp.repos.base import BaseRepo, CoreServices, RepoConfig, RepoStatus
from helm_release_mcp.repos.types.dify_helm.charts import ChartOperationsMixin
from helm_release_mcp.repos.types.dify_helm.release import ReleaseOperationsMixin


class DifyHelmRepo(ChartOperationsMixin, ReleaseOperationsMixin, BaseRepo, repo_type="dify-helm"):
    """Repository type for Dify Helm charts."""

    def __init__(self, config: RepoConfig, services: CoreServices) -> None:
        super().__init__(config, services)
        self.charts_path = self._get_setting("charts_path", "charts/")
        self.publish_workflow = self._get_setting("publish_workflow")
        self.release_trigger = self._get_setting("release_trigger", "release")

    async def get_status(self) -> RepoStatus:
        """Get the high-level status of this Helm registry."""
        latest = self.services.github.get_latest_release(self.github_path)
        latest_release = latest.tag_name if latest else None

        open_prs = self.services.github.list_open_prs(self.github_path)

        running = self.services.github.list_workflow_runs(
            self.github_path, status="in_progress", limit=10
        )

        return RepoStatus(
            name=self.name,
            github=self.github_path,
            type=self.repo_type,
            description=self.config.description,
            latest_release=latest_release,
            open_prs_count=len(open_prs),
            running_workflows_count=len(running),
            extra={
                "charts_path": self.charts_path,
            },
        )
