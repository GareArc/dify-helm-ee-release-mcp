"""Version management operations."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helm_release_mcp.repos.types.dify_enterprise.repo import DifyEnterpriseRepo


class VersionOperationsMixin:
    """Mixin providing version operations for DifyEnterpriseRepo."""

    async def get_version(self: "DifyEnterpriseRepo") -> dict[str, Any]:
        """Get the current application version."""
        await self.ensure_workspace()

        repo_path = self.services.workspace.get_repo_path(self.name)
        version_file_path = repo_path / self.version_file

        if not version_file_path.exists():
            return {
                "success": False,
                "error": f"Version file not found: {self.version_file}",
            }

        if self.version_file.endswith(".json"):
            data = self.services.files.read_json(version_file_path)
        else:
            data = self.services.files.read_yaml(version_file_path)

        try:
            version = self.services.files.get_nested_value(data, self.version_path)
        except KeyError:
            return {
                "success": False,
                "error": f"Version path not found: {self.version_path}",
            }

        return {
            "success": True,
            "version": version,
            "file": self.version_file,
        }

    async def bump_version(
        self: "DifyEnterpriseRepo",
        bump_type: str = "patch",
        *,
        new_version: str | None = None,
    ) -> dict[str, Any]:
        """Bump the application version."""
        await self.ensure_workspace()

        repo_path = self.services.workspace.get_repo_path(self.name)
        version_file_path = repo_path / self.version_file

        if self.version_file.endswith(".json"):
            data = self.services.files.read_json(version_file_path)
        else:
            data = self.services.files.read_yaml(version_file_path)

        old_version = self.services.files.get_nested_value(data, self.version_path)
        calculated_version = new_version or self._calculate_bump(old_version, bump_type)

        self.services.files.set_nested_value(data, self.version_path, calculated_version)

        if self.version_file.endswith(".json"):
            self.services.files.write_json(version_file_path, data)
        else:
            self.services.files.write_yaml(version_file_path, data)

        return {
            "success": True,
            "old_version": old_version,
            "new_version": calculated_version,
            "bump_type": bump_type if not new_version else "explicit",
        }

    def _calculate_bump(self: "DifyEnterpriseRepo", version: str, bump_type: str) -> str:
        """Calculate the next version based on bump type."""
        clean_version = version.lstrip("v")

        parts = clean_version.split(".")
        if len(parts) < 3:
            parts.extend(["0"] * (3 - len(parts)))

        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2].split("-")[0])

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1

        return f"{major}.{minor}.{patch}"
