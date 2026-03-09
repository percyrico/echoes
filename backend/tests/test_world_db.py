"""Tests for WorldDB — SQLite persistence layer."""

import json
import pytest
import pytest_asyncio

from services.world_db import WorldDB
from models.schemas import Scenario, GameState


@pytest_asyncio.fixture
async def db(tmp_path):
    """Fresh database per test."""
    db = WorldDB()
    db.db_path = str(tmp_path / "test.db")
    await db.initialize()
    yield db
    await db.close()


class TestWorldDB:
    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, db):
        """Tables should exist after init."""
        async with db._db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = [row[0] async for row in cursor]
        assert "sessions" in tables

    @pytest.mark.asyncio
    async def test_save_and_get_session(self, db):
        game_state = {"scenario": "last_train", "current_loop": 1, "clues": []}
        await db.save_session("sess-1", "last_train", game_state)

        result = await db.get_session("sess-1")
        assert result is not None
        assert result["id"] == "sess-1"
        assert result["scenario"] == "last_train"
        assert result["game_state"] == game_state

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, db):
        result = await db.get_session("does-not-exist")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_session_upsert(self, db):
        """Saving same session_id twice should update, not duplicate."""
        state_v1 = {"current_loop": 1}
        state_v2 = {"current_loop": 3}

        await db.save_session("sess-1", "last_train", state_v1)
        await db.save_session("sess-1", "last_train", state_v2)

        result = await db.get_session("sess-1")
        assert result["game_state"]["current_loop"] == 3

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, db):
        sessions = await db.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_sessions_multiple(self, db):
        await db.save_session("a", "last_train", {"loop": 1})
        await db.save_session("b", "dinner_party", {"loop": 2})
        await db.save_session("c", "the_signal", {"loop": 1})

        sessions = await db.list_sessions()
        assert len(sessions) == 3
        ids = {s["id"] for s in sessions}
        assert ids == {"a", "b", "c"}

    @pytest.mark.asyncio
    async def test_delete_session(self, db):
        await db.save_session("sess-del", "locked_room", {"data": True})
        await db.delete_session("sess-del")

        result = await db.get_session("sess-del")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_no_error(self, db):
        """Deleting a non-existent session should not raise."""
        await db.delete_session("ghost-session")  # should not raise

    @pytest.mark.asyncio
    async def test_complex_game_state_persistence(self, db):
        """Full GameState round-trip through DB."""
        state = GameState(
            session_id="complex-1",
            scenario=Scenario.LOCKED_ROOM,
            current_loop=4,
        )
        state_dict = state.to_dict()
        await db.save_session("complex-1", "locked_room", state_dict)

        result = await db.get_session("complex-1")
        restored = GameState(**result["game_state"])
        assert restored.session_id == "complex-1"
        assert restored.scenario == Scenario.LOCKED_ROOM
        assert restored.current_loop == 4

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, db):
        """Multiple rapid saves don't corrupt data."""
        import asyncio
        tasks = []
        for i in range(20):
            tasks.append(
                db.save_session(f"concurrent-{i}", "last_train", {"index": i})
            )
        await asyncio.gather(*tasks)

        sessions = await db.list_sessions()
        assert len(sessions) == 20
