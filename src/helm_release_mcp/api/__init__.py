from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from helm_release_mcp.settings import get_settings

router = APIRouter()


class HealthCheckResponse(BaseModel):
    status: str


security = HTTPBearer()


async def verify_token(bearer: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    token = bearer.credentials
    if token != get_settings().auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token


@router.get("/api/health")
async def api_health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="ok")

@router.get("/")
async def index():
    return RedirectResponse("/static/index.html")