# Dify Enterprise Repo Tools

## Overview

The Dify Enterprise repository is a monorepo that contains the source code for all Dify Enterprise services. It is hosted on GitHub at [langgenius/dify-enterprise](https://github.com/langgenius/dify-enterprise) with private access.

## Tools

### trigger_build_by_tagging

Trigger a build/CI workflow by tagging a release. Usually when a release branch is ready, we tag it with a version number like `v1.0.0` and trigger the build/CI workflow.

```yaml
- name: dify-enterprise
  github: langgenius/dify-enterprise
  type: dify-enterprise
  description: Dify Enterprise services monorepo
  settings:
    release_workflow: .github/workflows/release.yml
  ```
