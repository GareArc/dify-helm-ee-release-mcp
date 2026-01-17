"""Build and Helm chart update operations."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helm_release_mcp.repos.types.dify_enterprise.repo import DifyEnterpriseRepo


class BuildOperationsMixin:
    """Mixin providing build operations for DifyEnterpriseRepo."""

    async def trigger_build(
        self: "DifyEnterpriseRepo",
        *,
        ref: str | None = None,
    ) -> dict[str, Any]:
        """Trigger a build/CI workflow."""
        default_branch = self.services.github.get_default_branch(self.github_path)
        target_ref = ref or default_branch

        run_id = self.services.github.trigger_workflow(
            self.github_path,
            self.build_workflow,
            ref=target_ref,
        )

        return {
            "success": True,
            "workflow": self.build_workflow,
            "ref": target_ref,
            "run_id": run_id,
        }

    async def update_helm_chart(
        self: "DifyEnterpriseRepo",
        version: str | None = None,
    ) -> dict[str, Any]:
        """Update the associated Helm chart with the new app version."""
        if not self.helm_repo or not self.helm_chart:
            return {
                "success": False,
                "error": "Helm repo/chart not configured for this application",
            }

        if not version:
            version_result = await self.get_version()
            if not version_result["success"]:
                return version_result
            version = version_result["version"]

        return {
            "success": True,
            "helm_repo": self.helm_repo,
            "helm_chart": self.helm_chart,
            "app_version": version,
            "message": f"Would update {self.helm_chart} appVersion to {version} in {self.helm_repo}",
        }
