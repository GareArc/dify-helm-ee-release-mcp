from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from pydantic import BaseModel

from helm_release_mcp.api import verify_token

router = APIRouter()


class ToolCallItem(BaseModel):
    tool_call_id: str
    tool_name: str
    args: dict


class ToolCallResponse(BaseModel):
    items: list[ToolCallItem]


@router.get("/api/tool-calls")
async def api_tool_calls(_: Annotated[str, Depends(verify_token)]):
    return ToolCallResponse(
        items=[
            ToolCallItem(
                tool_call_id="xxx",
                tool_name="yyy",
                args={},
            ),
        ],
    )
