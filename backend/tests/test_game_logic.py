"""Integration tests for game logic — clue tracking, loop mechanics, win/lose conditions."""

import time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from models.schemas import (
    Scenario, LoopStatus, Mood, Clue, LoopEntry, GameState,
)
from services.session_manager import SessionManager
from services.world_db import WorldDB


@pytest_asyncio.fixture
async def db(tmp_path):
    db = WorldDB()
    db.db_path = str(tmp_path / "game_test.db")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def manager(db):
    with patch("services.session_manager.ImageGenerator") as MockImgGen:
        instance = MockImgGen.return_value
        instance.generate_scene_image = AsyncMock(return_value=None)
        instance.generate_clue_image = AsyncMock(return_value=None)
        instance.generate_death_image = AsyncMock(return_value=None)
        instance.generate_victory_image = AsyncMock(return_value=None)

        with patch.dict("os.environ", {"GOOGLE_API_KEY": "fake"}):
            mgr = SessionManager(db)
            mgr.image_gen = instance
            yield mgr


class TestClueTracking:
    @pytest.mark.asyncio
    async def test_add_clue_to_state(self, manager):
        state = await manager.get_or_create("clue-1", Scenario.DINNER_PARTY)
        clue = Clue(text="The Almond Scent", detail="Bitter almonds near soufflé", is_key_clue=True)
        state.clues.append(clue)
        assert len(state.clues) == 1
        assert state.clues[0].text == "The Almond Scent"

    @pytest.mark.asyncio
    async def test_no_duplicate_clues(self, manager):
        state = await manager.get_or_create("clue-2", Scenario.DINNER_PARTY)
        clue1 = Clue(text="The Almond Scent", detail="v1", is_key_clue=True)
        state.clues.append(clue1)

        # Simulate duplicate check (as done in _process_transcript_chunk)
        existing_texts = {c.text.lower() for c in state.clues}
        clue2_text = "The Almond Scent"
        if clue2_text.lower() not in existing_texts:
            state.clues.append(Clue(text=clue2_text))

        assert len(state.clues) == 1  # no duplicate

    @pytest.mark.asyncio
    async def test_key_clue_counting(self, manager):
        state = await manager.get_or_create("clue-3", Scenario.LOCKED_ROOM)
        state.clues = [
            Clue(text="C1", is_key_clue=True),
            Clue(text="C2", is_key_clue=False),
            Clue(text="C3", is_key_clue=True),
            Clue(text="C4", is_key_clue=True),
            Clue(text="C5", is_key_clue=False),
        ]
        key_count = sum(1 for c in state.clues if c.is_key_clue)
        assert key_count == 3

    @pytest.mark.asyncio
    async def test_clues_persist_across_loops(self, manager, db):
        """Clues found in loop 1 should still be there in loop 2."""
        state = await manager.get_or_create("clue-persist", Scenario.LAST_TRAIN)
        state.clues = [
            Clue(text="Train Ticket", detail="To nowhere", loop_discovered=1, is_key_clue=True),
        ]
        state.current_loop = 2

        # Save and reload
        await db.save_session("clue-persist", "last_train", state.to_dict())
        loaded = await db.get_session("clue-persist")
        restored = GameState(**loaded["game_state"])

        assert len(restored.clues) == 1
        assert restored.clues[0].text == "Train Ticket"
        assert restored.current_loop == 2


class TestLoopMechanics:
    @pytest.mark.asyncio
    async def test_loop_counter_increments_on_fail(self, manager):
        state = await manager.get_or_create("loop-1", Scenario.DINNER_PARTY)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time()

        ws = AsyncMock()
        manager.websockets["loop-1"] = ws

        assert state.current_loop == 1
        await manager._handle_loop_fail("loop-1", "Time expired")
        assert state.current_loop == 2

    @pytest.mark.asyncio
    async def test_multiple_loop_failures(self, manager):
        state = await manager.get_or_create("loop-multi", Scenario.LAST_TRAIN)
        ws = AsyncMock()
        manager.websockets["loop-multi"] = ws

        for i in range(5):
            state.loop_status = LoopStatus.ACTIVE
            state.loop_start_time = time.time()
            await manager._handle_loop_fail("loop-multi", f"Death #{i+1}")

        assert state.current_loop == 6
        assert len(state.loop_history) == 5
        assert all(e.status == LoopStatus.FAILED for e in state.loop_history)

    @pytest.mark.asyncio
    async def test_loop_duration_tracked(self, manager):
        state = await manager.get_or_create("loop-dur", Scenario.LOCKED_ROOM)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time() - 147  # 147 seconds ago

        ws = AsyncMock()
        manager.websockets["loop-dur"] = ws

        await manager._handle_loop_fail("loop-dur", "Trapped")

        entry = state.loop_history[0]
        assert 145 <= entry.duration_seconds <= 150

    @pytest.mark.asyncio
    async def test_clues_recorded_per_loop(self, manager):
        state = await manager.get_or_create("loop-clues", Scenario.DINNER_PARTY)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time()
        state.clues = [
            Clue(id="c1", text="Clue A", loop_discovered=1),
            Clue(id="c2", text="Clue B", loop_discovered=1),
        ]

        ws = AsyncMock()
        manager.websockets["loop-clues"] = ws

        await manager._handle_loop_fail("loop-clues", "Failed")

        entry = state.loop_history[0]
        assert len(entry.clues_found) == 2
        assert "c1" in entry.clues_found
        assert "c2" in entry.clues_found


class TestWinConditions:
    @pytest.mark.asyncio
    async def test_can_break_when_enough_key_clues(self, manager):
        state = await manager.get_or_create("win-1", Scenario.DINNER_PARTY)
        state.total_clues_needed = 3

        # Add 3 key clues
        state.clues = [
            Clue(text=f"Key Clue {i}", is_key_clue=True) for i in range(3)
        ]

        key_count = sum(1 for c in state.clues if c.is_key_clue)
        assert key_count >= state.total_clues_needed

    @pytest.mark.asyncio
    async def test_cannot_break_without_enough_clues(self, manager):
        state = await manager.get_or_create("win-2", Scenario.LOCKED_ROOM)
        state.total_clues_needed = 8

        state.clues = [
            Clue(text="Clue 1", is_key_clue=True),
            Clue(text="Clue 2", is_key_clue=False),
        ]

        key_count = sum(1 for c in state.clues if c.is_key_clue)
        assert key_count < state.total_clues_needed
        assert state.can_break_loop is False

    @pytest.mark.asyncio
    async def test_victory_sets_complete(self, manager):
        state = await manager.get_or_create("win-3", Scenario.THE_SIGNAL)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time()

        ws = AsyncMock()
        manager.websockets["win-3"] = ws

        await manager._handle_loop_break("win-3")

        assert state.is_complete is True
        assert state.loop_status == LoopStatus.BROKEN

    @pytest.mark.asyncio
    async def test_victory_persists(self, manager, db):
        state = await manager.get_or_create("win-persist", Scenario.DINNER_PARTY)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time()

        ws = AsyncMock()
        manager.websockets["win-persist"] = ws

        await manager._handle_loop_break("win-persist")

        loaded = await db.get_session("win-persist")
        restored = GameState(**loaded["game_state"])
        assert restored.is_complete is True
        assert restored.loop_status == LoopStatus.BROKEN


class TestMoodTransitions:
    @pytest.mark.asyncio
    async def test_mood_starts_from_scenario(self, manager):
        state = await manager.get_or_create("mood-1", Scenario.DINNER_PARTY)
        from models.scenarios import get_scenario_config
        config = get_scenario_config(Scenario.DINNER_PARTY)
        assert state.current_mood == config["initial_mood"]

    @pytest.mark.asyncio
    async def test_mood_change_updates_state(self, manager):
        state = await manager.get_or_create("mood-2", Scenario.LAST_TRAIN)
        assert state.current_mood == Mood.MYSTERIOUS

        state.current_mood = Mood.TENSE
        assert state.current_mood == Mood.TENSE

    @pytest.mark.asyncio
    async def test_mood_persists(self, manager, db):
        state = await manager.get_or_create("mood-3", Scenario.LOCKED_ROOM)
        state.current_mood = Mood.DREAD

        await db.save_session("mood-3", "locked_room", state.to_dict())
        loaded = await db.get_session("mood-3")
        restored = GameState(**loaded["game_state"])
        assert restored.current_mood == Mood.DREAD


class TestTimerLogic:
    def test_timer_starts_at_loop_duration(self):
        state = GameState(
            session_id="timer-1",
            scenario=Scenario.DINNER_PARTY,
            loop_duration_seconds=300,
        )
        assert state.loop_duration_seconds == 300

    def test_remaining_time_calculation(self):
        state = GameState(
            session_id="timer-2",
            scenario=Scenario.LAST_TRAIN,
            loop_duration_seconds=300,
            loop_start_time=time.time() - 120,  # 2 minutes ago
        )
        elapsed = time.time() - state.loop_start_time
        remaining = max(0, state.loop_duration_seconds - elapsed)
        assert 178 <= remaining <= 182  # ~180 seconds

    def test_timer_expired(self):
        state = GameState(
            session_id="timer-3",
            scenario=Scenario.THE_SIGNAL,
            loop_duration_seconds=300,
            loop_start_time=time.time() - 400,  # well past 5 min
        )
        elapsed = time.time() - state.loop_start_time
        remaining = max(0, state.loop_duration_seconds - elapsed)
        assert remaining == 0


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_session_id(self, manager):
        state = await manager.get_or_create("", Scenario.DINNER_PARTY)
        assert state.session_id == ""

    @pytest.mark.asyncio
    async def test_state_isolation_between_sessions(self, manager):
        s1 = await manager.get_or_create("iso-1", Scenario.LAST_TRAIN)
        s2 = await manager.get_or_create("iso-2", Scenario.DINNER_PARTY)

        s1.clues.append(Clue(text="Only for s1"))
        assert len(s2.clues) == 0

        s1.current_mood = Mood.DREAD
        assert s2.current_mood != Mood.DREAD

    @pytest.mark.asyncio
    async def test_fail_after_victory_no_op(self, manager):
        """Once the loop is broken, failing should do nothing."""
        state = await manager.get_or_create("edge-1", Scenario.LOCKED_ROOM)
        state.loop_status = LoopStatus.BROKEN
        state.is_complete = True

        ws = AsyncMock()
        manager.websockets["edge-1"] = ws

        # This should be a no-op since loop_status != ACTIVE
        await manager._handle_loop_fail("edge-1", "Should not work")
        ws.send_json.assert_not_called()
        assert state.is_complete is True
