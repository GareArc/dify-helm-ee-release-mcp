# Configuration Guide

This document explains how `config/repos.yaml` drives the MCP server's behavior.

## Overview

```
repos.yaml → RepoRegistry → Repo Instances → MCP Tools
```

The configuration file defines which repositories the server manages. At startup, the server:

1. Reads `repos.yaml`
2. Instantiates the appropriate repo class for each entry
3. Dynamically registers MCP tools based on each repo's operations

**No code changes needed to add new repositories—just update the config.**

## Configuration Schema

```yaml
repositories:
  - name: <string>           # Unique identifier, used in tool names
    github: <string>         # GitHub path "owner/repo"
    type: <string>           # Repository type (see below)
    description: <string>    # Optional description
    settings:                # Type-specific settings
      <key>: <value>
```

## Repository Types

### dify-helm

For the Dify Helm charts repository.

```yaml
- name: dify-helm
  github: langgenius/dify-helm
  type: dify-helm
  description: Dify Helm charts
  settings:
    charts_path: charts/           # Path to charts directory (default: "charts/")
    publish_workflow: publish.yaml # Workflow to trigger on publish
    release_trigger: release       # How to trigger release (see below)
```

**`release_trigger` options:**
| Value | Behavior | GitHub Workflow Trigger |
|-------|----------|------------------------|
| `tag` | Push git tag only | `on: push: tags:` |
| `release` | Create GitHub Release (default) | `on: release:` |
| `workflow` | Manual workflow dispatch | `on: workflow_dispatch:` |
| `release+workflow` | Both release + dispatch | Both triggers |

**Generated tools:**
| Tool | Description |
|------|-------------|
| `{name}__list_charts` | List all charts in the registry |
| `{name}__get_chart_info` | Get chart metadata |
| `{name}__prepare_release` | Bump version, create branch, open PR |
| `{name}__publish_release` | Merge PR, create tag and release |
| `{name}__lint_chart` | Validate chart structure |

### dify-enterprise

For the Dify Enterprise monorepo.

```yaml
- name: dify-enterprise
  github: langgenius/dify-enterprise
  type: dify-enterprise
  description: Dify Enterprise services monorepo
  settings:
    version_file: package.json     # File containing version
    version_path: version          # JSON/YAML path to version field
    build_workflow: ci.yaml        # CI workflow file
    release_workflow: release.yaml # Release workflow file
    release_trigger: release       # How to trigger release (see below)
    helm_repo: dify-helm           # Associated helm repo (optional)
    helm_chart: dify-enterprise    # Chart name in helm repo (optional)
```

**`release_trigger` options:**
| Value | Behavior | GitHub Workflow Trigger |
|-------|----------|------------------------|
| `tag` | Push git tag only | `on: push: tags:` |
| `release` | Create GitHub Release (default) | `on: release:` |
| `workflow` | Manual workflow dispatch | `on: workflow_dispatch:` |
| `release+workflow` | Both release + dispatch | Both triggers |

**Generated tools:**
| Tool | Description |
|------|-------------|
| `{name}__get_version` | Read current version from version file |
| `{name}__bump_version` | Increment version (major/minor/patch) |
| `{name}__prepare_release` | Bump version, create branch, open PR |
| `{name}__publish_release` | Merge PR, create tag and release |
| `{name}__trigger_build` | Trigger CI workflow |
| `{name}__update_helm_chart` | Update associated Helm chart appVersion |

## How It Works

### 1. Type Registration

Repo classes self-register using the `repo_type` parameter:

```python
class DifyHelmRepo(BaseRepo, repo_type="dify-helm"):
    ...

class DifyEnterpriseRepo(BaseRepo, repo_type="dify-enterprise"):
    ...
```

This populates `BaseRepo._type_registry`:
```python
{
    "dify-helm": DifyHelmRepo,
    "dify-enterprise": DifyEnterpriseRepo,
}
```

### 2. Config Loading

At startup, `RepoRegistry.from_config()` reads `repos.yaml`:

```python
for repo_data in config["repositories"]:
    repo_class = BaseRepo.get_type_class(repo_data["type"])
    repo = repo_class(config, services)
    registry.register(repo)
```

### 3. Tool Generation

Tools are dynamically created from repo methods:

```python
for repo in registry.get_all_repos():
    for operation in repo.get_operations():
        tool_name = f"{repo.name}__{operation.name}"
        # Register as MCP tool
```

Operations are discovered by introspecting async methods on the repo class.

## Example: Full Configuration

```yaml
repositories:
  # Dify Helm charts
  - name: dify-helm
    github: langgenius/dify-helm
    type: dify-helm
    description: Dify Helm charts
    settings:
      charts_path: charts/
      publish_workflow: publish.yaml

  # Dify Enterprise monorepo
  - name: dify-enterprise
    github: langgenius/dify-enterprise
    type: dify-enterprise
    description: Dify Enterprise services monorepo
    settings:
      version_file: package.json
      version_path: version
      build_workflow: ci.yaml
      release_workflow: release.yaml
      helm_repo: dify-helm
      helm_chart: dify-enterprise
```

This configuration generates these MCP tools:

```
# Dify Helm operations
dify-helm__list_charts
dify-helm__get_chart_info
dify-helm__prepare_release
dify-helm__publish_release
dify-helm__lint_chart

# Dify Enterprise operations  
dify-enterprise__get_version
dify-enterprise__bump_version
dify-enterprise__prepare_release
dify-enterprise__publish_release
dify-enterprise__trigger_build
dify-enterprise__update_helm_chart
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HELM_MCP_GITHUB_TOKEN` | Yes | - | GitHub Personal Access Token |
| `HELM_MCP_CONFIG_PATH` | No | `config/repos.yaml` | Path to configuration file |
| `HELM_MCP_WORKSPACE_DIR` | No | `~/.helm-release-mcp/workspace` | Directory for cloning repos |
| `HELM_MCP_LOG_LEVEL` | No | `INFO` | Logging level |

## Adding a New Repository Type

1. Create a new folder in `src/helm_release_mcp/repos/types/`:
   ```
   repos/types/my_type/
   ├── __init__.py
   ├── repo.py
   └── operations.py
   ```

2. Define the repo class with `repo_type`:
   ```python
   class MyTypeRepo(BaseRepo, repo_type="my-type"):
       async def get_status(self) -> RepoStatus:
           ...
       
       async def my_operation(self, arg: str) -> dict[str, Any]:
           ...
   ```

3. Export from `__init__.py`:
   ```python
   from .repo import MyTypeRepo
   __all__ = ["MyTypeRepo"]
   ```

4. Import in `repos/types/__init__.py`:
   ```python
   from .my_type import MyTypeRepo
   ```

5. Use in config:
   ```yaml
   - name: my_repo
     github: org/repo
     type: my-type
   ```
