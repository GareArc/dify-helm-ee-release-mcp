"""Workflow operations for Dify Helm repo."""

from typing import Any, Protocol, cast


class WorkflowRepoProtocol(Protocol):
    github: Any
    github_path: str

    def _get_setting(self, key: str, default: Any = None) -> Any: ...
    async def _trigger_workflow(
        self,
        workflow: str,
        branch: str,
        name: str,
    ) -> dict[str, Any]: ...


class WorkflowOperationsMixin:
    """Mixin providing workflow operations for DifyHelmRepo."""

    async def trigger_cve_scan(
        self,
        branch: str,
    ) -> dict[str, Any]:
        """Trigger container security scan workflow on a release branch."""
        repo = cast(WorkflowRepoProtocol, self)
        workflow = repo._get_setting("cve_scan_workflow")
        if not workflow:
            return {"success": False, "error": "cve_scan_workflow not configured"}

        return await repo._trigger_workflow(workflow, branch, "CVE scan")

    async def trigger_benchmark(
        self,
        branch: str,
    ) -> dict[str, Any]:
        """Trigger benchmark test workflow on a release branch."""
        repo = cast(WorkflowRepoProtocol, self)
        workflow = repo._get_setting("benchmark_workflow")
        if not workflow:
            return {"success": False, "error": "benchmark_workflow not configured"}

        return await repo._trigger_workflow(workflow, branch, "benchmark test")

    async def trigger_license_review(
        self,
        branch: str,
    ) -> dict[str, Any]:
        """Trigger dependency license review workflow on a release branch."""
        repo = cast(WorkflowRepoProtocol, self)
        workflow = repo._get_setting("license_review_workflow")
        if not workflow:
            return {"success": False, "error": "license_review_workflow not configured"}

        return await repo._trigger_workflow(workflow, branch, "license review")

    async def trigger_linear_checklist(
        self,
        branch: str,
    ) -> dict[str, Any]:
        """Trigger Linear release checklist workflow on a release branch."""
        repo = cast(WorkflowRepoProtocol, self)
        workflow = repo._get_setting("linear_checklist_workflow")
        if not workflow:
            return {"success": False, "error": "linear_checklist_workflow not configured"}

        return await repo._trigger_workflow(workflow, branch, "Linear checklist")

    async def release(
        self,
        branch: str,
    ) -> dict[str, Any]:
        """Trigger release workflow to publish Helm chart."""
        repo = cast(WorkflowRepoProtocol, self)
        workflow = repo._get_setting("release_workflow")
        if not workflow:
            return {"success": False, "error": "release_workflow not configured"}

        return await repo._trigger_workflow(workflow, branch, "release")

    async def _trigger_workflow(
        self,
        workflow: str,
        branch: str,
        name: str,
    ) -> dict[str, Any]:
        """Helper to trigger a workflow and return standardized result."""
        try:
            repo = cast(WorkflowRepoProtocol, self)
            run_id = repo.github.trigger_workflow(
                repo.github_path,
                workflow,
                ref=branch,
            )

            return {
                "success": True,
                "workflow": workflow,
                "branch": branch,
                "run_id": run_id,
                "message": f"Triggered {name} workflow",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to trigger {name}: {e}",
            }
