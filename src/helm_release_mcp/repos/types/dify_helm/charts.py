"""Chart listing and inspection operations."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helm_release_mcp.repos.types.dify_helm.repo import DifyHelmRepo


class ChartOperationsMixin:
    """Mixin providing chart operations for DifyHelmRepo."""

    async def list_charts(self: "DifyHelmRepo") -> dict[str, Any]:
        """List all Helm charts in the registry."""
        await self.ensure_workspace()

        repo_path = self.services.workspace.get_repo_path(self.name)
        charts_dir = repo_path / self.charts_path

        charts = []
        if charts_dir.exists():
            for item in charts_dir.iterdir():
                if item.is_dir() and (item / "Chart.yaml").exists():
                    chart_data = self.services.files.read_yaml(item / "Chart.yaml")
                    charts.append(
                        {
                            "name": chart_data.get("name", item.name),
                            "version": chart_data.get("version", "unknown"),
                            "appVersion": chart_data.get("appVersion"),
                            "description": chart_data.get("description", ""),
                        }
                    )

        return {
            "success": True,
            "charts": charts,
            "count": len(charts),
        }

    async def get_chart_info(self: "DifyHelmRepo", chart: str) -> dict[str, Any]:
        """Get detailed information about a specific chart."""
        await self.ensure_workspace()

        repo_path = self.services.workspace.get_repo_path(self.name)
        chart_path = repo_path / self.charts_path / chart

        if not chart_path.exists():
            return {
                "success": False,
                "error": f"Chart not found: {chart}",
            }

        chart_yaml = chart_path / "Chart.yaml"
        if not chart_yaml.exists():
            return {
                "success": False,
                "error": f"Chart.yaml not found for: {chart}",
            }

        chart_data = self.services.files.read_yaml(chart_yaml)
        values_yaml = chart_path / "values.yaml"

        return {
            "success": True,
            "name": chart_data.get("name", chart),
            "version": chart_data.get("version"),
            "appVersion": chart_data.get("appVersion"),
            "description": chart_data.get("description"),
            "type": chart_data.get("type", "application"),
            "dependencies": chart_data.get("dependencies", []),
            "maintainers": chart_data.get("maintainers", []),
            "has_values": values_yaml.exists(),
        }

    async def lint_chart(self: "DifyHelmRepo", chart: str) -> dict[str, Any]:
        """Lint a Helm chart for errors."""
        await self.ensure_workspace()

        repo_path = self.services.workspace.get_repo_path(self.name)
        chart_path = repo_path / self.charts_path / chart

        if not chart_path.exists():
            return {
                "success": False,
                "error": f"Chart not found: {chart}",
            }

        issues = []

        chart_yaml = chart_path / "Chart.yaml"
        if not chart_yaml.exists():
            issues.append("Missing Chart.yaml")
        else:
            chart_data = self.services.files.read_yaml(chart_yaml)
            if not chart_data.get("name"):
                issues.append("Chart.yaml missing 'name' field")
            if not chart_data.get("version"):
                issues.append("Chart.yaml missing 'version' field")

        templates_dir = chart_path / "templates"
        if not templates_dir.exists():
            issues.append("Missing templates directory")

        return {
            "success": len(issues) == 0,
            "chart": chart,
            "issues": issues,
            "message": "Chart is valid" if not issues else f"Found {len(issues)} issue(s)",
        }
