"""Repository registry for managing repository instances."""

import logging
from pathlib import Path
from typing import Any

from helm_release_mcp.core.files import FileService
from helm_release_mcp.core.git import GitService
from helm_release_mcp.core.github import GitHubService
from helm_release_mcp.core.workspace import WorkspaceManager
from helm_release_mcp.repos.base import BaseRepo, CoreServices, RepoConfig

# Import repo types to register them
from helm_release_mcp.repos.types.application import ApplicationRepo  # noqa: F401
from helm_release_mcp.repos.types.helm_registry import HelmRegistryRepo  # noqa: F401

logger = logging.getLogger(__name__)


class RepoRegistry:
    """Registry for managing repository instances.

    Loads repository definitions from config and instantiates
    the appropriate repo type classes.
    """

    def __init__(self, services: CoreServices) -> None:
        """Initialize the registry.

        Args:
            services: Core services container.
        """
        self._services = services
        self._repos: dict[str, BaseRepo] = {}
        self._configs: dict[str, RepoConfig] = {}

    @classmethod
    def from_config(
        cls,
        config_path: Path,
        *,
        github_token: str,
        workspace_dir: Path,
        github_api_base_url: str = "https://api.github.com",
    ) -> "RepoRegistry":
        """Create a registry from a config file.

        Args:
            config_path: Path to repos.yaml config file.
            github_token: GitHub personal access token.
            workspace_dir: Directory for local clones.
            github_api_base_url: GitHub API base URL.

        Returns:
            Initialized RepoRegistry.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config is invalid.
        """
        # Initialize core services
        git_service = GitService()
        github_service = GitHubService(github_token, github_api_base_url)
        file_service = FileService()
        workspace_manager = WorkspaceManager(workspace_dir, git_service, github_token)

        services = CoreServices(
            git=git_service,
            github=github_service,
            files=file_service,
            workspace=workspace_manager,
        )

        registry = cls(services)
        registry.load_config(config_path)
        return registry

    def load_config(self, config_path: Path) -> None:
        """Load repository configurations from a YAML file.

        Args:
            config_path: Path to repos.yaml.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config is invalid.
        """
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return

        data = self._services.files.read_yaml(config_path)
        repos_data = data.get("repositories") or []

        if not isinstance(repos_data, list):
            raise ValueError("Invalid config: 'repositories' must be a list")

        for repo_data in repos_data:
            self._load_repo(repo_data)

    def _load_repo(self, repo_data: dict[str, Any]) -> None:
        """Load a single repository from config data.

        Args:
            repo_data: Repository configuration dictionary.
        """
        # Validate required fields
        required = ["name", "github", "type"]
        for field in required:
            if field not in repo_data:
                raise ValueError(f"Repository config missing required field: {field}")

        config = RepoConfig(
            name=repo_data["name"],
            github=repo_data["github"],
            type=repo_data["type"],
            description=repo_data.get("description", ""),
            settings=repo_data.get("settings", {}),
        )

        # Get the repo type class
        repo_class = BaseRepo.get_type_class(config.type)
        if repo_class is None:
            logger.warning(
                f"Unknown repo type '{config.type}' for '{config.name}'. "
                f"Available types: {BaseRepo.get_registered_types()}"
            )
            return

        # Instantiate the repo
        repo = repo_class(config, self._services)
        self._repos[config.name] = repo
        self._configs[config.name] = config

        logger.info(f"Loaded repo: {config.name} ({config.type})")

    def get_repo(self, name: str) -> BaseRepo | None:
        """Get a repository by name.

        Args:
            name: Repository name.

        Returns:
            The repository, or None if not found.
        """
        return self._repos.get(name)

    def get_config(self, name: str) -> RepoConfig | None:
        """Get a repository config by name.

        Args:
            name: Repository name.

        Returns:
            The config, or None if not found.
        """
        return self._configs.get(name)

    def list_repos(self) -> list[str]:
        """List all repository names.

        Returns:
            List of repository names.
        """
        return list(self._repos.keys())

    def get_all_repos(self) -> dict[str, BaseRepo]:
        """Get all repositories.

        Returns:
            Dictionary of name to repo.
        """
        return dict(self._repos)

    def get_repos_by_type(self, repo_type: str) -> list[BaseRepo]:
        """Get all repositories of a specific type.

        Args:
            repo_type: Repository type identifier.

        Returns:
            List of matching repositories.
        """
        return [repo for repo in self._repos.values() if repo.repo_type == repo_type]

    @property
    def services(self) -> CoreServices:
        """Get the core services."""
        return self._services

    def close(self) -> None:
        """Clean up resources."""
        self._services.github.close()
