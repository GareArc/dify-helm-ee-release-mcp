"""File operations service for YAML/JSON manipulation."""

import json
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class FileService:
    """Service for file operations with YAML/JSON support.

    Uses ruamel.yaml to preserve formatting, comments, and order in YAML files.
    """

    def __init__(self) -> None:
        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._yaml.indent(mapping=2, sequence=4, offset=2)

    def read_yaml(self, path: Path) -> dict[str, Any]:
        """Read a YAML file and return its contents.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed YAML contents as a dictionary.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file cannot be parsed.
        """
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")

        try:
            with path.open("r") as f:
                data = self._yaml.load(f)
                return dict(data) if data else {}
        except Exception as e:
            raise ValueError(f"Failed to parse YAML file {path}: {e}") from e

    def write_yaml(self, path: Path, data: dict[str, Any]) -> None:
        """Write data to a YAML file, preserving formatting.

        Args:
            path: Path to the YAML file.
            data: Data to write.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            self._yaml.dump(data, f)

    def update_yaml(
        self,
        path: Path,
        updates: dict[str, Any],
        *,
        merge_deep: bool = False,
    ) -> dict[str, Any]:
        """Update specific keys in a YAML file.

        Args:
            path: Path to the YAML file.
            updates: Dictionary of key-value pairs to update.
            merge_deep: If True, merge nested dictionaries recursively.

        Returns:
            The updated data.
        """
        data = self.read_yaml(path)

        if merge_deep:
            self._deep_merge(data, updates)
        else:
            data.update(updates)

        self.write_yaml(path, data)
        return data

    def read_json(self, path: Path) -> dict[str, Any]:
        """Read a JSON file and return its contents.

        Args:
            path: Path to the JSON file.

        Returns:
            Parsed JSON contents as a dictionary.
        """
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {path}")

        with path.open("r") as f:
            return json.load(f)

    def write_json(self, path: Path, data: dict[str, Any], *, indent: int = 2) -> None:
        """Write data to a JSON file.

        Args:
            path: Path to the JSON file.
            data: Data to write.
            indent: Indentation level for pretty printing.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(data, f, indent=indent)
            f.write("\n")

    def get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get a value from a nested dictionary using dot notation.

        Args:
            data: The dictionary to search.
            path: Dot-separated path (e.g., "metadata.version").

        Returns:
            The value at the path.

        Raises:
            KeyError: If the path doesn't exist.
        """
        keys = path.split(".")
        result = data
        for key in keys:
            if not isinstance(result, dict):
                raise KeyError(f"Cannot traverse non-dict at key: {key}")
            result = result[key]
        return result

    def set_nested_value(self, data: dict[str, Any], path: str, value: Any) -> None:
        """Set a value in a nested dictionary using dot notation.

        Args:
            data: The dictionary to modify.
            path: Dot-separated path (e.g., "metadata.version").
            value: The value to set.
        """
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def _deep_merge(self, base: dict[str, Any], updates: dict[str, Any]) -> None:
        """Recursively merge updates into base dictionary."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
