"""Release operations for Dify Enterprise."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helm_release_mcp.repos.types.dify_enterprise.repo import DifyEnterpriseRepo


class ReleaseOperationsMixin:
    """Mixin providing release operations for DifyEnterpriseRepo."""

    async def prepare_release(
        self: "DifyEnterpriseRepo",
        version: str,
        *,
        changelog: str | None = None,
    ) -> dict[str, Any]:
        """Prepare a new application release."""
        await self.ensure_workspace()

        repo_path = self.services.workspace.get_repo_path(self.name)

        branch_name = f"release/{version}"
        default_branch = self.services.github.get_default_branch(self.github_path)

        repo = self.services.workspace.prepare_branch(
            self.name,
            branch_name,
            start_point=f"origin/{default_branch}",
        )

        bump_result = await self.bump_version(new_version=version)
        old_version = bump_result["old_version"]

        version_file_path = repo_path / self.version_file
        commit_msg = f"Bump version to {version}"

        self.services.git.commit(
            repo,
            commit_msg,
            files=[str(version_file_path.relative_to(repo_path))],
        )
        self.services.git.push(repo, set_upstream=True)

        pr_body = f"## Release v{version}\n\n**Previous version:** {old_version}\n**New version:** {version}\n"
        if changelog:
            pr_body += f"\n### Changelog\n\n{changelog}\n"

        pr = self.services.github.create_pr(
            self.github_path,
            title=f"Release v{version}",
            body=pr_body,
            head=branch_name,
            base=default_branch,
        )

        return {
            "success": True,
            "old_version": old_version,
            "new_version": version,
            "branch": branch_name,
            "pr_number": pr.number,
            "pr_url": pr.html_url,
        }

    async def publish_release(
        self: "DifyEnterpriseRepo",
        pr_number: int,
        *,
        merge_method: str = "squash",
    ) -> dict[str, Any]:
        """Publish a release by merging PR and triggering release.

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

        version_result = await self.get_version()
        version = version_result.get("version", "unknown")

        tag_name = f"v{version}"
        trigger = self.release_trigger
        result: dict[str, Any] = {
            "success": True,
            "version": version,
            "tag": tag_name,
            "trigger": trigger,
        }

        if trigger == "tag":
            self.services.github.create_tag(
                self.github_path,
                tag_name=tag_name,
                message=f"Release v{version}",
                sha=pr.head_sha,
            )
            result["triggered_by"] = "tag push"

        elif trigger == "release":
            release = self.services.github.create_release(
                self.github_path,
                tag_name=tag_name,
                name=f"Release {tag_name}",
                body=f"Release of version {version}",
            )
            result["release_url"] = release.html_url
            result["triggered_by"] = "github release"

        elif trigger == "workflow":
            if not self.release_workflow:
                return {
                    "success": False,
                    "error": "release_trigger is 'workflow' but release_workflow not configured",
                }
            run_id = self.services.github.trigger_workflow(
                self.github_path,
                self.release_workflow,
                ref=pr.base_ref,
                inputs={"version": version},
            )
            result["workflow_run_id"] = run_id
            result["triggered_by"] = "workflow dispatch"

        elif trigger == "release+workflow":
            release = self.services.github.create_release(
                self.github_path,
                tag_name=tag_name,
                name=f"Release {tag_name}",
                body=f"Release of version {version}",
            )
            result["release_url"] = release.html_url

            if self.release_workflow:
                try:
                    run_id = self.services.github.trigger_workflow(
                        self.github_path,
                        self.release_workflow,
                        ref=tag_name,
                        inputs={"version": version},
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
