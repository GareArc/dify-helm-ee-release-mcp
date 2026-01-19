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
      github_token: <string> # Optional: per-repo GitHub token
      <key>: <value>
```

## Repository Types

### dify

For the Dify core services repository (public). Used to create release branches from any git ref (tag, branch, or SHA).

```yaml
- name: dify
  github: langgenius/dify
  type: dify
  description: Dify core services
  settings:
    github_token: ${DIFY_GITHUB_TOKEN}  # Optional
```

**Generated tools:**
| Tool | Description |
|------|-------------|
| `{name}__create_release_branch` | Create a release branch from any git ref (tag, branch, or SHA) |

### dify-helm

For the Dify Helm charts repository. Manages pre-release checks and release workflows.

```yaml
- name: dify-helm
  github: langgenius/dify-helm
  type: dify-helm
  description: Dify Helm charts
  settings:
    github_token: ${DIFY_HELM_GITHUB_TOKEN}  # Optional
    cve_scan_workflow: .github/workflows/cve.yaml
    benchmark_workflow: .github/workflows/benchmark.yaml
    license_review_workflow: .github/workflows/enterprise-license.yaml
    linear_checklist_workflow: .github/workflows/linear-checklist.yaml
    release_workflow: .github/workflows/release.yaml
```

**Settings:**
| Setting | Description |
|---------|-------------|
| `cve_scan_workflow` | Workflow for container security scanning |
| `benchmark_workflow` | Workflow for benchmark/pressure tests |
| `license_review_workflow` | Workflow for dependency license review |
| `linear_checklist_workflow` | Workflow for Linear release checklist |
| `release_workflow` | Workflow to publish Helm chart to gh-pages |

**Generated tools:**
| Tool | Description |
|------|-------------|
| `{name}__trigger_cve_scan` | Trigger container security scan on a release branch |
| `{name}__trigger_benchmark` | Trigger benchmark test on a release branch |
| `{name}__trigger_license_review` | Trigger dependency license review on a release branch |
| `{name}__trigger_linear_checklist` | Trigger Linear release checklist on a release branch |
| `{name}__release` | Trigger release workflow to publish Helm chart |

### dify-enterprise

For the Dify Enterprise monorepo (private). Triggers builds by creating tags on release branches.

```yaml
- name: dify-enterprise
  github: langgenius/dify-enterprise
  type: dify-enterprise
  description: Dify Enterprise services monorepo
  settings:
    github_token: ${DIFY_ENTERPRISE_GITHUB_TOKEN}  # Optional
```

**Generated tools:**
| Tool | Description |
|------|-------------|
| `{name}__create_tag` | Create a tag on a branch to trigger build/CI workflow |

### dify-enterprise-frontend

For the Dify Enterprise Frontend repository (private). Triggers builds by creating tags on release branches.

```yaml
- name: dify-enterprise-frontend
  github: langgenius/dify-enterprise-frontend
  type: dify-enterprise-frontend
  description: Dify Enterprise frontend
  settings:
    github_token: ${DIFY_ENTERPRISE_FRONTEND_GITHUB_TOKEN}  # Optional
```

**Generated tools:**
| Tool | Description |
|------|-------------|
| `{name}__create_tag` | Create a tag on a branch to trigger build/CI workflow |

## How It Works

### 1. Type Registration

Repo classes self-register using the `repo_type` parameter:

```python
class DifyRepo(BaseRepo, repo_type="dify"):
    ...

class DifyHelmRepo(BaseRepo, repo_type="dify-helm"):
    ...

class DifyEnterpriseRepo(BaseRepo, repo_type="dify-enterprise"):
    ...

class DifyEnterpriseFrontendRepo(BaseRepo, repo_type="dify-enterprise-frontend"):
    ...
```

This populates `BaseRepo._type_registry`:
```python
{
    "dify": DifyRepo,
    "dify-helm": DifyHelmRepo,
    "dify-enterprise": DifyEnterpriseRepo,
    "dify-enterprise-frontend": DifyEnterpriseFrontendRepo,
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
  # Dify core services (public)
  - name: dify
    github: langgenius/dify
    type: dify
    description: Dify core services
    settings:
      github_token: ${DIFY_GITHUB_TOKEN}

  # Dify Helm charts (private)
  - name: dify-helm
    github: langgenius/dify-helm
    type: dify-helm
    description: Dify Helm charts
    settings:
      github_token: ${DIFY_HELM_GITHUB_TOKEN}
      cve_scan_workflow: .github/workflows/cve.yaml
      benchmark_workflow: .github/workflows/benchmark.yaml
      license_review_workflow: .github/workflows/enterprise-license.yaml
      linear_checklist_workflow: .github/workflows/linear-checklist.yaml
      release_workflow: .github/workflows/release.yaml

  # Dify Enterprise monorepo (private)
  - name: dify-enterprise
    github: langgenius/dify-enterprise
    type: dify-enterprise
    description: Dify Enterprise services monorepo
    settings:
      github_token: ${DIFY_ENTERPRISE_GITHUB_TOKEN}

  # Dify Enterprise Frontend (private)
  - name: dify-enterprise-frontend
    github: langgenius/dify-enterprise-frontend
    type: dify-enterprise-frontend
    description: Dify Enterprise frontend
    settings:
      github_token: ${DIFY_ENTERPRISE_FRONTEND_GITHUB_TOKEN}
```

This configuration generates these MCP tools:

```
# Global tools (always available)
list_repos
get_repo_status
create_branch
get_release_branch_info

# Dify operations
dify__create_release_branch

# Dify Helm operations
dify-helm__trigger_cve_scan
dify-helm__trigger_benchmark
dify-helm__trigger_license_review
dify-helm__trigger_linear_checklist
dify-helm__release

# Dify Enterprise operations  
dify-enterprise__create_tag

# Dify Enterprise Frontend operations  
dify-enterprise-frontend__create_tag
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HELM_MCP_GITHUB_TOKEN` | Yes | - | Default GitHub Personal Access Token |
| `HELM_MCP_AUTH_TOKEN` | No | - | Shared bearer token required for MCP HTTP transports |
| `HELM_MCP_AUTH_ISSUER_URL` | No | - | OAuth issuer URL used for auth metadata |
| `HELM_MCP_AUTH_RESOURCE_URL` | No | - | OAuth resource server URL used for auth metadata |
| `HELM_MCP_TRANSPORT` | No | `stdio` | MCP transport (`stdio`, `sse`, `streamable-http`) |
| `HELM_MCP_HOST` | No | `127.0.0.1` | Host interface for HTTP transports |
| `HELM_MCP_PORT` | No | `8000` | Port for HTTP transports |
| `HELM_MCP_CONFIG_PATH` | No | `config/repos.yaml` | Path to configuration file |
| `HELM_MCP_WORKSPACE_DIR` | No | `~/.helm-release-mcp/workspace` | Directory for cloning repos |
| `HELM_MCP_LOG_LEVEL` | No | `INFO` | Logging level |

## Per-Repository Tokens

Repositories can use different GitHub tokens by specifying `github_token` in settings:

```yaml
repositories:
  - name: dify-helm
    github: langgenius/dify-helm
    type: dify-helm
    settings:
      github_token: ${DIFY_HELM_GITHUB_TOKEN}
      cve_scan_workflow: .github/workflows/cve.yaml

  - name: dify-enterprise
    github: langgenius/dify-enterprise
    type: dify-enterprise
    settings:
      github_token: ${DIFY_ENTERPRISE_GITHUB_TOKEN}
```

If `github_token` is not specified, the default `HELM_MCP_GITHUB_TOKEN` is used.

### Environment Variable Interpolation

`repos.yaml` supports `${ENV_VAR}` interpolation for string values. Missing variables resolve to an empty string.

### MCP HTTP Authentication

When running MCP over SSE or Streamable HTTP, you can enable a shared bearer token by setting `HELM_MCP_AUTH_TOKEN`. The server will require the header `Authorization: Bearer <token>` on all MCP HTTP requests.

If your client expects OAuth metadata, set `HELM_MCP_AUTH_ISSUER_URL` and `HELM_MCP_AUTH_RESOURCE_URL`. These are used only for auth metadata and do not change token validation.

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
