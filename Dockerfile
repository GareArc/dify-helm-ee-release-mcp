# syntax=docker/dockerfile:1

# ============================================================================
# Build stage
# ============================================================================
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ ./src/

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================================================
# Runtime stage
# ============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy config directory structure
COPY config/ ./config/

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV HELM_MCP_CONFIG_PATH=/app/config/repos.yaml
ENV HELM_MCP_WORKSPACE_DIR=/app/workspace

# Create workspace directory
RUN mkdir -p /app/workspace && chown -R appuser:appuser /app

USER appuser

# Health check - verify the module can be imported
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from helm_release_mcp import main" || exit 1

ENTRYPOINT ["helm-release-mcp"]
