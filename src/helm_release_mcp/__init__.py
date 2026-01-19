"""Helm Release MCP Server - Automate Helm chart releases across GitHub repositories."""

import uvicorn
from fastapi import FastAPI

from helm_release_mcp.api import router
from helm_release_mcp.api.tool_calls import router as tool_calls_router
from helm_release_mcp.server import create_server
from helm_release_mcp.settings import get_settings


def main() -> None:
    settings = get_settings()
    server = create_server()

    if settings.transport == "stdio":
        server.run(settings.transport)
    else:
        mcp_app = server.http_app(path="/mcp")
        app = FastAPI(
            lifespan=mcp_app.lifespan,
        )
        app.include_router(router)
        app.include_router(tool_calls_router)
        app.mount("/", mcp_app)
        uvicorn.run(app, host=settings.host, port=settings.port)
