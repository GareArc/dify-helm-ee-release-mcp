from typing import Literal
from pydantic import BaseModel, Field
from fastmcp.tools import FunctionTool
from helm_release_mcp.redis.client import TypedRedisClient
from helm_release_mcp.settings import get_settings
from functools import wraps
from typing import Callable, Any
from datetime import datetime, timedelta
import uuid
import asyncio

REDIS_KEY_TOOL_CALLS = "dify_helm_mcp:tool_calls"


class ToolCall(BaseModel):
    tool_call_id: str
    tool_name: str
    args: dict
    status: Literal["pending", "approved", "rejected"]
    expires: datetime = Field(default_factory=lambda: datetime.now() + timedelta(seconds=120))


class ToolCallService:
    def __init__(self) -> None:
        self.redis_client = TypedRedisClient()

    def add_tool_call(self, tool_call: ToolCall) -> None:
        self.redis_client.hset(REDIS_KEY_TOOL_CALLS, tool_call.tool_call_id, tool_call)

    def get_tool_call(self, tool_call_id: str) -> ToolCall | None:
        return self.redis_client.hget(ToolCall, REDIS_KEY_TOOL_CALLS, tool_call_id)

    def list_tool_calls(self) -> list[ToolCall]:
        return [ToolCall.model_validate_json(value) for value in self.redis_client.hgetall(REDIS_KEY_TOOL_CALLS)]

    def approve_tool_call(self, tool_call_id: str) -> None:
        tool_call = self.get_tool_call(tool_call_id)
        if tool_call is None:
            raise ValueError(f"Tool call {tool_call_id} not found")
        tool_call.status = "approved"
        self.redis_client.hset(REDIS_KEY_TOOL_CALLS, tool_call_id, tool_call)

    def reject_tool_call(self, tool_call_id: str) -> None:
        tool_call = self.get_tool_call(tool_call_id)
        if tool_call is None:
            raise ValueError(f"Tool call {tool_call_id} not found")
        tool_call.status = "rejected"
        self.redis_client.hset(REDIS_KEY_TOOL_CALLS, tool_call_id, tool_call)

    def delete_tool_call(self, tool_call_id: str) -> None:
        self.redis_client.hdel(REDIS_KEY_TOOL_CALLS, tool_call_id)


class ToolCallApprovalError(Exception):
    """Exception raised when a tool call is rejected or times out."""

    def __init__(self, message: str, tool_call_id: str, tool_name: str) -> None:
        super().__init__(message)
        self.tool_call_id = tool_call_id
        self.tool_name = tool_name


class ToolCallRejectedError(ToolCallApprovalError):
    """Exception raised when a tool call is rejected."""

    pass


class ToolCallTimeoutError(ToolCallApprovalError):
    """Exception raised when a tool call approval times out."""

    pass



tool_call_service = ToolCallService()

def aapprove_required(
) -> Callable:
    """Decorator that requires approval before executing an MCP tool.

    When a decorated tool is invoked:
    1. Creates a tool call entry in Redis with status "pending"
    2. Blocks and polls until approved/rejected/timeout
    3. If approved, proceeds with execution
    4. If rejected or timeout, raises a human-readable exception

    Args:
        timeout_seconds: Maximum seconds to wait for approval (default: 120).
        poll_interval: Seconds between status checks (default: 0.5).

    Returns:
        Decorator function.

    Raises:
        ToolCallRejectedError: If the tool call is rejected.
        ToolCallTimeoutError: If approval times out.
    """
    def decorator(func: Callable) -> Callable:
        settings = get_settings()
        timeout_seconds = settings.human_in_the_loop_timeout_seconds
        poll_interval = 1

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not settings.human_in_the_loop_enabled:
                return await func(*args, **kwargs)
            tool_name = func.__name__
            tool_call_id = str(uuid.uuid4())

            # Create tool call entry
            tool_call = ToolCall(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                args={"args": list(args), "kwargs": kwargs},
                status="pending",
                expires=datetime.now() + timedelta(seconds=timeout_seconds),
            )
            tool_call_service.add_tool_call(tool_call)

            # Poll for approval/rejection/timeout
            start_time = datetime.now()
            while True:
                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout_seconds:
                    tool_call_service.delete_tool_call(tool_call_id)
                    raise ToolCallTimeoutError(
                        f"Tool call '{tool_name}' timed out after {timeout_seconds} seconds. "
                        f"Tool call ID: {tool_call_id}",
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                    )

                # Check status
                current_tool_call = tool_call_service.get_tool_call(tool_call_id)
                if current_tool_call is None:
                    # Tool call was deleted (shouldn't happen, but handle gracefully)
                    raise ToolCallRejectedError(
                        f"Tool call '{tool_name}' was not found. It may have been deleted.",
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                    )

                if current_tool_call.status == "approved":
                    # Clean up and proceed
                    tool_call_service.delete_tool_call(tool_call_id)
                    return await func(*args, **kwargs)

                if current_tool_call.status == "rejected":
                    # Clean up and raise exception
                    tool_call_service.delete_tool_call(tool_call_id)
                    raise ToolCallRejectedError(
                        f"Tool call '{tool_name}' was rejected. Tool call ID: {tool_call_id}",
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                    )

                # Still pending, wait and poll again
                await asyncio.sleep(poll_interval)

        return async_wrapper

    return decorator