from pydantic import BaseModel
from fastapi import APIRouter
from fastapi import Request
from fastapi import HTTPException
from typing import Annotated
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from helm_release_mcp.settings import get_settings
from fastapi import Depends

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
