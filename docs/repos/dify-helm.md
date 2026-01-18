# Dify Helm Repo Tools

## Overview

The Dify Helm repository is a standalone repo that contains the source code for all Dify Helm charts. It is hosted on GitHub at [langgenius/dify-helm](https://github.com/langgenius/dify-helm) with private access.

## Jobs

### UAT Deployment

We use this repo to deploy the UAT environment of Dify Enterprise prior to official release.

### Pre-release Checks

When release branch is merged into main branch, some workflows will be triggered to check if the release is ready to be released. Including pressure tests, CVE scans, and more. These checks can be manually triggered in case some release branches never get merged into main branch.

### Release

Release is a manually triggered action, we specify the branch name that follows a fixed naming convention like `release/1.0.0` and trigger the release workflow.

### Publish

The release workflow will publish the Helm chart to the gh-pages branch for public access. Right after release, it generates a defualt sidebar entry and a version description page. Usually we just modify the branch directly with proper information and push which triggers gh-pages workflow.

## Tools

### trigger_contianer_security_scan

Trigger a container security scan workflow on a specific release branch.

```yaml
- name: dify-helm
  github: langgenius/dify-helm
  type: dify-helm
  description: Dify Helm charts
  settings:
    container_security_scan_workflow: .github/workflows/cve.yaml
  ```

### trigger_linear_release_checklist

Trigger a linear release checklist workflow on a specific release branch.

```yaml
- name: dify-helm
  github: langgenius/dify-helm
  type: dify-helm
  description: Dify Helm charts
  settings:
    linear_release_checklist_workflow: .github/workflows/linear-checklist.yaml
  ```

### trigger_benchmark_test

Trigger a benchmark test workflow on a specific release branch.

```yaml
- name: dify-helm
  github: langgenius/dify-helm
  type: dify-helm
  description: Dify Helm charts
  settings:
    benchmark_test_workflow: .github/workflows/benchmark.yaml
  ```

### trigger_enterprise_dependency_license_review

Trigger a dependency license review workflow on a specific release branch.

```yaml
- name: dify-helm
  github: langgenius/dify-helm
  type: dify-helm
  description: Dify Helm charts
  settings:
    dependency_license_review_workflow: .github/workflows/enterprise-license.yaml
  ```

### release

Release the Helm chart to the gh-pages branch.

```yaml
- name: dify-helm
  github: langgenius/dify-helm
  type: dify-helm
  description: Dify Helm charts
  settings:
    release_workflow: .github/workflows/release.yaml
  ```
