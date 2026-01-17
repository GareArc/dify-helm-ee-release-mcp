"""Dify Enterprise repository type."""

from helm_release_mcp.repos.base import BaseRepo, CoreServices, RepoConfig, RepoStatus
from helm_release_mcp.repos.types.dify_enterprise.build import BuildOperationsMixin
from helm_release_mcp.repos.types.dify_enterprise.release import ReleaseOperationsMixin
from helm_release_mcp.repos.types.dify_enterprise.version import VersionOperationsMixin


class DifyEnterpriseRepo(
    VersionOperationsMixin,
    ReleaseOperationsMixin,
    BuildOperationsMixin,
    BaseRepo,
    repo_type="dify-enterprise",
):
    """Repository type for Dify Enterprise monorepo."""

    def __init__(self, config: RepoConfig, services: CoreServices) -> None:
        super().__init__(config, services)
        self.version_file = self._get_setting("version_file", "package.json")
        self.version_path = self._get_setting("version_path", "version")
        self.build_workflow = self._get_setting("build_workflow", "ci.yaml")
        self.release_workflow = self._get_setting("release_workflow", "release.yaml")
        self.release_trigger = self._get_setting("release_trigger", "release")
        self.helm_repo = self._get_setting("helm_repo")
        self.helm_chart = self._get_setting("helm_chart")

    async def get_status(self) -> RepoStatus:
        """Get the high-level status of this application repository."""
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
                "version_file": self.version_file,
                "helm_repo": self.helm_repo,
                "helm_chart": self.helm_chart,
            },
        )
