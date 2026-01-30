"""Tool call storage and approval workflow for human-in-the-loop functionality.

This module provides storage backends for managing tool call approvals.
The default `MemoryBasedToolCallStore` is suitable for single-process deployments.

## Multi-Process Limitations

The `MemoryBasedToolCallStore` stores data in-memory within a single process.
This has the following limitations:

- **Not suitable for multi-process deployments**: Each process maintains its own
  independent store. Tool calls created in one process will not be visible to
  other processes.
- **Not suitable for multi-worker deployments**: If using uvicorn/gunicorn with
  multiple workers, each worker is a separate process with its own store.
- **Data is lost on restart**: All pending tool calls are lost when the process
  restarts.

For multi-process deployments, consider implementing a shared storage backend
(e.g., Redis, database) by subclassing `ToolCallStore`.

## Coroutine Safety

The `MemoryBasedToolCallStore` is safe for concurrent access from multiple
coroutines within the same event loop. It uses `asyncio.Lock` to ensure
thread-safe operations in an async context.
"""

from typing import Literal, Optional, Callable, Any
from pydantic import BaseModel, Field
from helm_release_mcp.settings import get_settings
from functools import wraps
from datetime import datetime, timedelta
import uuid
import asyncio
from abc import ABC, abstractmethod


class ToolCall(BaseModel):
    tool_call_id: str
    tool_name: str
    args: dict
    status: Literal["pending", "approved", "rejected"]
    expires: datetime = Field(default_factory=lambda: datetime.now() + timedelta(seconds=120))


class ToolCallStore(ABC):
    """Abstract base class for tool call storage backends.
    
    Implementations must be coroutine-safe for concurrent access within
    the same event loop.
    
    Note: The default singleton instance is NOT safe for multi-process
    deployments. See module docstring for details.
    """

    _instance: Optional["ToolCallStore"] = None

    @classmethod
    def get_instance(cls) -> "ToolCallStore":
        """Get or create the singleton store instance.
        
        Warning: This singleton is process-local. In multi-process deployments
        (e.g., multiple uvicorn workers), each process will have its own
        independent store instance.
        """
        if cls._instance is not None:
            return cls._instance
        cls._instance = MemoryBasedToolCallStore()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Primarily for testing."""
        cls._instance = None
        
    @abstractmethod
    async def add_tool_call(self, tool_call: ToolCall) -> None:
        pass
    @abstractmethod
    async def get_tool_call(self, tool_call_id: str) -> ToolCall | None:
        pass
    @abstractmethod
    async def list_tool_calls(self) -> list[ToolCall]:
        pass
    @abstractmethod
    async def update_tool_call(self, tool_call: ToolCall) -> None:
        pass
    @abstractmethod
    async def delete_tool_call(self, tool_call_id: str) -> None:
        pass


class MemoryBasedToolCallStore(ToolCallStore):
    """In-memory tool call store with coroutine-safe operations.
    
    This store maintains tool calls in memory using a dictionary for O(1) lookups.
    All operations are protected by an asyncio.Lock for safe concurrent access
    from multiple coroutines.
    
    Limitations:
        - Data is not persisted across process restarts
        - Not suitable for multi-process deployments (each process has its own store)
        - Not suitable for multi-worker server configurations
    
    For production multi-process deployments, implement a shared storage backend
    (e.g., Redis, PostgreSQL) by subclassing ToolCallStore.
    """
    
    def __init__(self) -> None:
        self._store: dict[str, ToolCall] = {}
        self._lock = asyncio.Lock()

    async def add_tool_call(self, tool_call: ToolCall) -> None:
        """Add a new tool call to the store."""
        async with self._lock:
            self._store[tool_call.tool_call_id] = tool_call

    async def get_tool_call(self, tool_call_id: str) -> ToolCall | None:
        """Retrieve a tool call by ID, or None if not found."""
        async with self._lock:
            return self._store.get(tool_call_id)

    async def list_tool_calls(self) -> list[ToolCall]:
        """List all tool calls, sorted by expiration time."""
        async with self._lock:
            return sorted(
                self._store.values(),
                key=lambda x: x.expires,
            )

    async def update_tool_call(self, tool_call: ToolCall) -> None:
        """Update an existing tool call."""
        async with self._lock:
            self._store[tool_call.tool_call_id] = tool_call

    async def delete_tool_call(self, tool_call_id: str) -> None:
        """Delete a tool call by ID. No-op if not found."""
        async with self._lock:
            self._store.pop(tool_call_id, None)


class ToolCallService:
    def __init__(self) -> None:
        self.tool_call_store = ToolCallStore.get_instance()

    async def add_tool_call(self, tool_call: ToolCall) -> None:
        await self.tool_call_store.add_tool_call(tool_call)

    async def get_tool_call(self, tool_call_id: str) -> ToolCall | None:
        return await self.tool_call_store.get_tool_call(tool_call_id)

    async def list_tool_calls(self) -> list[ToolCall]:
        return await self.tool_call_store.list_tool_calls()

    async def approve_tool_call(self, tool_call_id: str) -> None:
        tool_call = await self.get_tool_call(tool_call_id)
        tool_call.status = "approved"
        await self.tool_call_store.update_tool_call(tool_call)

    async def reject_tool_call(self, tool_call_id: str) -> None:
        tool_call = await self.get_tool_call(tool_call_id)
        tool_call.status = "rejected"
        await self.tool_call_store.update_tool_call(tool_call)

    async def delete_tool_call(self, tool_call_id: str) -> None:
        await self.tool_call_store.delete_tool_call(tool_call_id)


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


def aapprove_required() -> Callable:
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
            await tool_call_service.add_tool_call(tool_call)

            # Poll for approval/rejection/timeout
            start_time = datetime.now()
            while True:
                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout_seconds:
                    await tool_call_service.delete_tool_call(tool_call_id)
                    raise ToolCallTimeoutError(
                        f"Tool call '{tool_name}' timed out after {timeout_seconds} seconds. "
                        f"Tool call ID: {tool_call_id}",
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                    )

                # Check status
                current_tool_call = await tool_call_service.get_tool_call(tool_call_id)
                if current_tool_call is None:
                    # Tool call was deleted (shouldn't happen, but handle gracefully)
                    raise ToolCallRejectedError(
                        f"Tool call '{tool_name}' was not found. It may have been deleted.",
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                    )

                if current_tool_call.status == "approved":
                    # Clean up and proceed
                    await tool_call_service.delete_tool_call(tool_call_id)
                    return await func(*args, **kwargs)

                if current_tool_call.status == "rejected":
                    # Clean up and raise exception
                    await tool_call_service.delete_tool_call(tool_call_id)
                    raise ToolCallRejectedError(
                        f"Tool call '{tool_name}' was rejected. Tool call ID: {tool_call_id}",
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                    )

                # Still pending, wait and poll again
                await asyncio.sleep(poll_interval)

        return async_wrapper

    return decorator
