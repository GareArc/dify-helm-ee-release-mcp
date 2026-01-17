"""Release operations for Dify Helm charts."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helm_release_mcp.repos.types.dify_helm.repo import DifyHelmRepo


class ReleaseOperationsMixin:
    """Mixin providing release operations for DifyHelmRepo."""

    async def prepare_release(
        self: "DifyHelmRepo",
        chart: str,
        version: str,
        *,
        changelog: str | None = None,
        app_version: str | None = None,
    ) -> dict[str, Any]:
        """Prepare a new chart release by bumping version and creating PR."""
        await self.ensure_workspace()

        repo_path = self.services.workspace.get_repo_path(self.name)
        chart_path = repo_path / self.charts_path / chart
        chart_yaml = chart_path / "Chart.yaml"

        if not chart_yaml.exists():
            return {
                "success": False,
                "error": f"Chart not found: {chart}",
            }

        branch_name = f"release/{chart}-{version}"
        default_branch = self.services.github.get_default_branch(self.github_path)

        repo = self.services.workspace.prepare_branch(
            self.name,
            branch_name,
            start_point=f"origin/{default_branch}",
        )

        chart_data = self.services.files.read_yaml(chart_yaml)
        old_version = chart_data.get("version", "unknown")

        updates: dict[str, Any] = {"version": version}
        if app_version:
            updates["appVersion"] = app_version

        self.services.files.update_yaml(chart_yaml, updates)

        commit_msg = f"Bump {chart} to {version}"
        self.services.git.commit(
            repo,
            commit_msg,
            files=[str(chart_yaml.relative_to(repo_path))],
        )
        self.services.git.push(repo, set_upstream=True)

        pr_body = f"## Release {chart} v{version}\n\n**Previous version:** {old_version}\n**New version:** {version}\n"
        if app_version:
            pr_body += f"**App version:** {app_version}\n"
        if changelog:
            pr_body += f"\n### Changelog\n\n{changelog}\n"

        pr = self.services.github.create_pr(
            self.github_path,
            title=f"Release {chart} v{version}",
            body=pr_body,
            head=branch_name,
            base=default_branch,
        )

        return {
            "success": True,
            "chart": chart,
            "old_version": old_version,
            "new_version": version,
            "branch": branch_name,
            "pr_number": pr.number,
            "pr_url": pr.html_url,
        }

    async def publish_release(
        self: "DifyHelmRepo",
        chart: str,
        pr_number: int,
        *,
        merge_method: str = "squash",
    ) -> dict[str, Any]:
        """Publish a chart release by merging PR and triggering release.

        Trigger behavior controlled by `release_trigger` setting:
        - "tag": Push tag only (triggers workflows with `on: push: tags:`)
        - "release": Create GitHub release (triggers `on: release:`)
        - "workflow": Trigger workflow dispatch manually
        - "release+workflow": Create release AND trigger workflow
        """
        pr = self.services.github.get_pr(self.github_path, pr_number)

        if pr.merged:
            return {
                "success": False,
                "error": f"PR #{pr_number} is already merged",
            }

        if pr.state != "open":
            return {
                "success": False,
                "error": f"PR #{pr_number} is not open (state: {pr.state})",
            }

        merged = self.services.github.merge_pr(
            self.github_path,
            pr_number,
            merge_method=merge_method,
        )

        if not merged:
            return {
                "success": False,
                "error": f"Failed to merge PR #{pr_number}",
            }

        await self.ensure_workspace()
        repo_path = self.services.workspace.get_repo_path(self.name)
        chart_path = repo_path / self.charts_path / chart
        chart_data = self.services.files.read_yaml(chart_path / "Chart.yaml")
        version = chart_data.get("version", "unknown")

        tag_name = f"{chart}-{version}"
        trigger = self.release_trigger
        result: dict[str, Any] = {
            "success": True,
            "chart": chart,
            "version": version,
            "tag": tag_name,
            "trigger": trigger,
        }

        if trigger == "tag":
            self.services.github.create_tag(
                self.github_path,
                tag_name=tag_name,
                message=f"Release {chart} v{version}",
                sha=pr.head_sha,
            )
            result["triggered_by"] = "tag push"

        elif trigger == "release":
            release = self.services.github.create_release(
                self.github_path,
                tag_name=tag_name,
                name=f"{chart} v{version}",
                body=f"Release of {chart} version {version}",
            )
            result["release_url"] = release.html_url
            result["triggered_by"] = "github release"

        elif trigger == "workflow":
            if not self.publish_workflow:
                return {
                    "success": False,
                    "error": "release_trigger is 'workflow' but publish_workflow not configured",
                }
            run_id = self.services.github.trigger_workflow(
                self.github_path,
                self.publish_workflow,
                ref=pr.base_ref,
                inputs={"chart": chart, "version": version},
            )
            result["workflow_run_id"] = run_id
            result["triggered_by"] = "workflow dispatch"

        elif trigger == "release+workflow":
            release = self.services.github.create_release(
                self.github_path,
                tag_name=tag_name,
                name=f"{chart} v{version}",
                body=f"Release of {chart} version {version}",
            )
            result["release_url"] = release.html_url

            if self.publish_workflow:
                try:
                    run_id = self.services.github.trigger_workflow(
                        self.github_path,
                        self.publish_workflow,
                        ref=tag_name,
                        inputs={"chart": chart, "version": version},
                    )
                    result["workflow_run_id"] = run_id
                except Exception:
                    pass
            result["triggered_by"] = "github release + workflow dispatch"

        else:
            return {
                "success": False,
                "error": f"Unknown release_trigger: {trigger}",
            }

        return result
