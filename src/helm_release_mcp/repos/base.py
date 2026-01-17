"""Base repository class defining the interface for all repo types."""

import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from helm_release_mcp.core.files import FileService
from helm_release_mcp.core.git import GitService
from helm_release_mcp.core.github import GitHubService
from helm_release_mcp.core.workspace import WorkspaceManager

logger = logging.getLogger(__name__)


@dataclass
class RepoConfig:
    """Configuration for a repository."""

    name: str
    github: str  # "owner/repo" format
    type: str
    description: str = ""
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class RepoStatus:
    """High-level status of a repository."""

    name: str
    github: str
    type: str
    description: str
    latest_release: str | None = None
    open_prs_count: int = 0
    running_workflows_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationInfo:
    """Information about a repository operation."""

    name: str
    description: str
    parameters: list[dict[str, Any]]
    returns: str


@dataclass
class CoreServices:
    """Container for core services passed to repos."""

    git: GitService
    github: GitHubService
    files: FileService
    workspace: WorkspaceManager


class BaseRepo(ABC):
    """Abstract base class for repository types.

    Each repository type (helm-registry, application, etc.) extends this class
    and implements its specific operations as async methods.

    Operations are automatically discovered by introspecting async methods
    that don't start with underscore.
    """

    # Registry of repo type classes
    _type_registry: dict[str, type["BaseRepo"]] = {}

    def __init__(self, config: RepoConfig, services: CoreServices) -> None:
        """Initialize the repository.

        Args:
            config: Repository configuration.
            services: Core services container.
        """
        self.config = config
        self.services = services
        self._operations: dict[str, OperationInfo] | None = None

    def __init_subclass__(cls, repo_type: str | None = None, **kwargs: Any) -> None:
        """Register subclasses in the type registry."""
        super().__init_subclass__(**kwargs)
        if repo_type:
            BaseRepo._type_registry[repo_type] = cls

    @classmethod
    def get_type_class(cls, repo_type: str) -> type["BaseRepo"] | None:
        """Get the class for a repository type.

        Args:
            repo_type: Type identifier (e.g., "helm-registry").

        Returns:
            The repo class, or None if not found.
        """
        return cls._type_registry.get(repo_type)

    @classmethod
    def get_registered_types(cls) -> list[str]:
        """Get all registered repository types."""
        return list(cls._type_registry.keys())

    @property
    def name(self) -> str:
        """Repository name."""
        return self.config.name

    @property
    def github_path(self) -> str:
        """GitHub path (owner/repo)."""
        return self.config.github

    @property
    def repo_type(self) -> str:
        """Repository type identifier."""
        return self.config.type

    @abstractmethod
    async def get_status(self) -> RepoStatus:
        """Get the high-level status of this repository.

        Returns:
            Repository status information.
        """
        ...

    def get_operations(self) -> dict[str, OperationInfo]:
        """Get all available operations for this repository.

        Operations are discovered by introspecting async methods that:
        - Don't start with underscore
        - Are not 'get_status' or 'get_operations'
        - Have proper docstrings

        Returns:
            Dictionary of operation name to operation info.
        """
        if self._operations is not None:
            return self._operations

        self._operations = {}
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            # Skip private methods and base methods
            if name.startswith("_"):
                continue
            if name in ("get_status", "get_operations"):
                continue

            # Only include async methods
            if not inspect.iscoroutinefunction(method):
                continue

            # Extract info from docstring and signature
            sig = inspect.signature(method)
            doc = inspect.getdoc(method) or ""

            # Parse docstring for description and returns
            lines = doc.split("\n")
            description = lines[0] if lines else name
            returns = "dict"  # Default

            # Extract parameters
            parameters = []
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                param_info: dict[str, Any] = {
                    "name": param_name,
                    "required": param.default is inspect.Parameter.empty,
                }

                # Get type hint
                if param.annotation is not inspect.Parameter.empty:
                    param_info["type"] = str(param.annotation)
                else:
                    param_info["type"] = "Any"

                # Get default value
                if param.default is not inspect.Parameter.empty:
                    param_info["default"] = param.default

                parameters.append(param_info)

            self._operations[name] = OperationInfo(
                name=name,
                description=description,
                parameters=parameters,
                returns=returns,
            )

        return self._operations

    def get_operation_method(
        self, operation_name: str
    ) -> Callable[..., Coroutine[Any, Any, dict[str, Any]]] | None:
        """Get the method for an operation.

        Args:
            operation_name: Operation name.

        Returns:
            The async method, or None if not found.
        """
        operations = self.get_operations()
        if operation_name not in operations:
            return None
        return getattr(self, operation_name, None)

    async def ensure_workspace(self) -> None:
        """Ensure the repository is cloned and up to date."""
        default_branch = self.services.github.get_default_branch(self.github_path)
        self.services.workspace.ensure_repo(
            self.name,
            self.github_path,
            branch=default_branch,
        )

    def _get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Setting key.
            default: Default value if not found.

        Returns:
            The setting value.
        """
        return self.config.settings.get(key, default)
