# Helm Release MCP Server

MCP (Model Context Protocol) server for automating Dify EE Helm chart releases across GitHub repositories.

## Features

- **Multi-repo management**: Configure and manage multiple repositories from a single server
- **Helm chart releases**: Prepare and publish Helm chart releases with version bumping and PR workflows
- **Application releases**: Manage application version bumping, builds, and releases
- **GitHub integration**: Full support for PRs, releases, and workflow triggers
- **Flexible configuration**: YAML-based repository configuration

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- GitHub Personal Access Token (see below)

### GitHub Token Setup

Create a **Fine-Grained Personal Access Token** at [GitHub Settings → Developer settings → Fine-grained tokens](https://github.com/settings/tokens?type=beta):

| Permission | Access Level | Required For |
|------------|--------------|--------------|
| **Contents** | Read & Write | Clone, commit, push, create branches |
| **Pull requests** | Read & Write | Create and merge PRs |
| **Actions** | Read & Write | Trigger workflows, check run status |
| **Metadata** | Read | Required for API access |

**Repository access**: Select "Only select repositories" and choose the repos you'll manage, or "All repositories" for org-wide access.

### Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/helm-release-mcp.git
cd helm-release-mcp

# Install dependencies
uv sync
```

### Configuration

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your GitHub token:

   ```
   HELM_MCP_GITHUB_TOKEN=ghp_your_token_here
   ```

3. Configure your repositories in `config/repos.yaml`:

   ```yaml
   repositories:
     - name: dify-helm
       github: langgenius/dify-helm
       type: dify-helm
       description: Dify Helm charts
       settings:
         charts_path: charts/
         publish_workflow: publish.yaml
   ```

   See [docs/configuration.md](docs/configuration.md) for full configuration reference.

### Running the Server

```bash
uv run helm-release-mcp
```

### MCP Client Configuration

For Claude Desktop, add to your MCP settings:

```json
{
  "mcpServers": {
    "helm-release": {
      "command": "uv",
      "args": ["--directory", "/path/to/helm-release-mcp", "run", "helm-release-mcp"],
      "env": {
        "HELM_MCP_GITHUB_TOKEN": "ghp_xxxx"
      }
    }
  }
}
```

## Available Tools

### Discovery Tools

- `list_repos()` - List all managed repositories
- `get_repo_status(repo)` - Get high-level status of a repository
- `get_repo_operations(repo)` - Get available operations for a repository

### Status Tools

- `check_workflow(repo, run_id)` - Check workflow run status
- `check_pr(repo, pr_number)` - Check pull request status
- `wait_for_workflow(repo, run_id)` - Wait for workflow completion
- `list_workflow_runs(repo)` - List recent workflow runs
- `list_open_prs(repo)` - List open pull requests

### Dify Helm Operations

- `dify-helm__list_charts()` - List all charts
- `dify-helm__get_chart_info(chart)` - Get chart details
- `dify-helm__prepare_release(chart, version)` - Create release PR
- `dify-helm__publish_release(chart, pr_number)` - Merge PR and release
- `dify-helm__lint_chart(chart)` - Validate a chart

### Dify Enterprise Operations

- `dify-enterprise__get_version()` - Get current version
- `dify-enterprise__bump_version(bump_type)` - Bump version
- `dify-enterprise__prepare_release(version)` - Create release PR
- `dify-enterprise__trigger_build(ref)` - Trigger CI workflow
- `dify-enterprise__publish_release(pr_number)` - Merge PR and release
- `dify-enterprise__update_helm_chart(version)` - Update Helm chart

## Example Workflow

```
1. list_repos()                                    # Discover available repos
2. dify-helm__prepare_release("api", "2.0.0")      # Create release PR
3. check_pr("dify-helm", 123)                      # Monitor PR status
4. dify-helm__publish_release("api", 123)          # Merge and release
5. check_workflow("dify-helm", 456)                # Monitor publish workflow
```

## Repository Types

### dify-helm

For the Dify Helm charts repository. Supports:

- Chart listing and inspection
- Version bumping with PR workflow
- Release publishing with tag creation
- Optional publish workflow trigger

### dify-enterprise

For the Dify Enterprise monorepo. Supports:

- Version file management (package.json, etc.)
- Semantic version bumping (major/minor/patch)
- Build workflow triggering
- Helm chart update coordination

## Development

```bash
# Install dev dependencies
uv sync

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/

# Run tests
uv run pytest
```

## License

MIT
