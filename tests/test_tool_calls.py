"""Tests for tool call storage backends.

These tests verify coroutine safety of the MemoryBasedToolCallStore
under concurrent access patterns.
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from helm_release_mcp.core.tool_calls import (
    MemoryBasedToolCallStore,
    ToolCall,
    ToolCallStore,
)


@pytest.fixture
def store() -> MemoryBasedToolCallStore:
    """Create a fresh store instance for each test."""
    return MemoryBasedToolCallStore()


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before and after each test."""
    ToolCallStore.reset_instance()
    yield
    ToolCallStore.reset_instance()


def make_tool_call(tool_call_id: str, status: str = "pending") -> ToolCall:
    """Helper to create a ToolCall with minimal required fields."""
    return ToolCall(
        tool_call_id=tool_call_id,
        tool_name="test_tool",
        args={"key": "value"},
        status=status,
        expires=datetime.now() + timedelta(seconds=120),
    )


class TestMemoryBasedToolCallStore:
    """Unit tests for MemoryBasedToolCallStore."""

    async def test_add_and_get(self, store: MemoryBasedToolCallStore):
        """Test basic add and get operations."""
        tc = make_tool_call("tc-1")
        await store.add_tool_call(tc)

        result = await store.get_tool_call("tc-1")
        assert result is not None
        assert result.tool_call_id == "tc-1"
        assert result.tool_name == "test_tool"

    async def test_get_nonexistent(self, store: MemoryBasedToolCallStore):
        """Test getting a non-existent tool call returns None."""
        result = await store.get_tool_call("nonexistent")
        assert result is None

    async def test_list_tool_calls(self, store: MemoryBasedToolCallStore):
        """Test listing tool calls."""
        tc1 = make_tool_call("tc-1")
        tc2 = make_tool_call("tc-2")
        await store.add_tool_call(tc1)
        await store.add_tool_call(tc2)

        result = await store.list_tool_calls()
        assert len(result) == 2
        assert {tc.tool_call_id for tc in result} == {"tc-1", "tc-2"}

    async def test_list_sorted_by_expires(self, store: MemoryBasedToolCallStore):
        """Test that list_tool_calls returns items sorted by expiration."""
        now = datetime.now()
        tc1 = ToolCall(
            tool_call_id="tc-later",
            tool_name="test",
            args={},
            status="pending",
            expires=now + timedelta(seconds=200),
        )
        tc2 = ToolCall(
            tool_call_id="tc-sooner",
            tool_name="test",
            args={},
            status="pending",
            expires=now + timedelta(seconds=100),
        )
        await store.add_tool_call(tc1)
        await store.add_tool_call(tc2)

        result = await store.list_tool_calls()
        assert result[0].tool_call_id == "tc-sooner"
        assert result[1].tool_call_id == "tc-later"

    async def test_update_tool_call(self, store: MemoryBasedToolCallStore):
        """Test updating a tool call."""
        tc = make_tool_call("tc-1", status="pending")
        await store.add_tool_call(tc)

        tc.status = "approved"
        await store.update_tool_call(tc)

        result = await store.get_tool_call("tc-1")
        assert result is not None
        assert result.status == "approved"

    async def test_delete_tool_call(self, store: MemoryBasedToolCallStore):
        """Test deleting a tool call."""
        tc = make_tool_call("tc-1")
        await store.add_tool_call(tc)

        await store.delete_tool_call("tc-1")
        result = await store.get_tool_call("tc-1")
        assert result is None

    async def test_delete_nonexistent(self, store: MemoryBasedToolCallStore):
        """Test that deleting a non-existent tool call doesn't raise."""
        # Should not raise
        await store.delete_tool_call("nonexistent")


class TestCoroutineSafety:
    """Tests verifying coroutine safety under concurrent access."""

    async def test_concurrent_adds(self, store: MemoryBasedToolCallStore):
        """Test that concurrent add operations are safe."""
        num_tasks = 100

        async def add_task(i: int):
            tc = make_tool_call(f"tc-{i}")
            await store.add_tool_call(tc)

        # Run all adds concurrently
        await asyncio.gather(*[add_task(i) for i in range(num_tasks)])

        # Verify all were added
        result = await store.list_tool_calls()
        assert len(result) == num_tasks

    async def test_concurrent_reads_and_writes(self, store: MemoryBasedToolCallStore):
        """Test concurrent reads and writes don't cause race conditions."""
        # Pre-populate some data
        for i in range(10):
            await store.add_tool_call(make_tool_call(f"initial-{i}"))

        errors: list[Exception] = []
        results: list[ToolCall | None] = []

        async def writer(i: int):
            try:
                tc = make_tool_call(f"new-{i}")
                await store.add_tool_call(tc)
            except Exception as e:
                errors.append(e)

        async def reader(i: int):
            try:
                # Read an existing item
                result = await store.get_tool_call(f"initial-{i % 10}")
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Mix readers and writers
        tasks = []
        for i in range(50):
            tasks.append(writer(i))
            tasks.append(reader(i))

        await asyncio.gather(*tasks)

        # No errors should have occurred
        assert len(errors) == 0
        # All reads should have succeeded
        assert all(r is not None for r in results)

    async def test_concurrent_updates(self, store: MemoryBasedToolCallStore):
        """Test that concurrent updates to the same item are safe."""
        tc = make_tool_call("tc-shared", status="pending")
        await store.add_tool_call(tc)

        update_count = 50
        statuses = ["pending", "approved", "rejected"]

        async def updater(i: int):
            tc_copy = make_tool_call("tc-shared", status=statuses[i % 3])
            await store.update_tool_call(tc_copy)

        await asyncio.gather(*[updater(i) for i in range(update_count)])

        # The item should still exist and have a valid status
        result = await store.get_tool_call("tc-shared")
        assert result is not None
        assert result.status in statuses

    async def test_concurrent_add_delete_same_id(self, store: MemoryBasedToolCallStore):
        """Test concurrent add and delete of the same ID."""
        test_id = "tc-contested"

        async def adder():
            for _ in range(20):
                tc = make_tool_call(test_id)
                await store.add_tool_call(tc)
                await asyncio.sleep(0)  # Yield to allow interleaving

        async def deleter():
            for _ in range(20):
                await store.delete_tool_call(test_id)
                await asyncio.sleep(0)  # Yield to allow interleaving

        # Run both concurrently - should not raise
        await asyncio.gather(adder(), deleter())

        # Final state: either exists or doesn't, but no corruption
        result = await store.get_tool_call(test_id)
        # Result can be None or a valid ToolCall
        if result is not None:
            assert result.tool_call_id == test_id

    async def test_high_contention_list(self, store: MemoryBasedToolCallStore):
        """Test listing under high contention with adds and deletes."""
        # Pre-populate
        for i in range(20):
            await store.add_tool_call(make_tool_call(f"pre-{i}"))

        list_results: list[list[ToolCall]] = []
        errors: list[Exception] = []

        async def lister():
            try:
                for _ in range(10):
                    result = await store.list_tool_calls()
                    list_results.append(result)
                    await asyncio.sleep(0)
            except Exception as e:
                errors.append(e)

        async def modifier():
            try:
                for i in range(10):
                    await store.add_tool_call(make_tool_call(f"mod-{i}"))
                    await store.delete_tool_call(f"pre-{i}")
                    await asyncio.sleep(0)
            except Exception as e:
                errors.append(e)

        await asyncio.gather(lister(), lister(), modifier(), modifier())

        # No errors should have occurred
        assert len(errors) == 0
        # All list results should be valid (non-empty lists with valid items)
        for result in list_results:
            assert isinstance(result, list)
            for tc in result:
                assert isinstance(tc, ToolCall)


class TestSingletonBehavior:
    """Tests for the singleton pattern."""

    async def test_singleton_returns_same_instance(self):
        """Test that get_instance returns the same instance."""
        instance1 = ToolCallStore.get_instance()
        instance2 = ToolCallStore.get_instance()
        assert instance1 is instance2

    async def test_reset_instance(self):
        """Test that reset_instance clears the singleton."""
        instance1 = ToolCallStore.get_instance()
        ToolCallStore.reset_instance()
        instance2 = ToolCallStore.get_instance()
        assert instance1 is not instance2
