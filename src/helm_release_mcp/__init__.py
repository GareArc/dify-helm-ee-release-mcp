"""Helm Release MCP Server - Automate Helm chart releases across GitHub repositories."""

from pathlib import Path
from helm_release_mcp.server import create_server
from helm_release_mcp.settings import get_settings
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from contextlib import asynccontextmanager
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from helm_release_mcp.api import router
from helm_release_mcp.api.tool_calls import router as tool_calls_router


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

        if settings.human_in_the_loop_enabled:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            app.include_router(router)
            app.include_router(tool_calls_router)
            app.mount("/static", StaticFiles(directory="static"), name="static")
        
        app.mount("/", mcp_app)
        uvicorn.run(app, host=settings.host, port=settings.port)
