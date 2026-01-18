# Dify Repo Tools

## Overview

The Dify repository contains the source code for all Dify core services. It is hosted on GitHub at [langgenius/dify](https://github.com/langgenius/dify) with public access. It is mainly served for the community version of Dify. In enterprise edition, we add some enterprise-specific features to this repo and build product with special branches. Each time we release a new EE version, we create a new release branch based on a specific community version and add some enterprise-specific changes to it.

## Tools

### create_release_branch

Create a new release branch based on a specific community version.

```yaml
- name: dify
  github: langgenius/dify
  type: dify
  description: Dify core services
  settings:
```
