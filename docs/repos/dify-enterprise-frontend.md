# Dify Enterprise Frontend Repo Tools

## Overview

The Dify Enterprise Frontend repository is a seperate repo for dify enterprise dashboard frontend. It is hosted on GitHub at [langgenius/dify-enterprise-frontend](https://github.com/langgenius/dify-enterprise-frontend) with private access.

## Tools

### trigger_build_by_tagging

Trigger a build/CI workflow by tagging a release. Usually when a release branch is ready, we tag it with a version number like `v1.0.0` and trigger the build/CI workflow.

```yaml
- name: dify-enterprise-frontend
  github: langgenius/dify-enterprise-frontend
  type: dify-enterprise-frontend
  description: Dify Enterprise frontend
  settings:
    release_workflow: .github/workflows/release.yml
  ```

