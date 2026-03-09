"""Tests for SessionManager — core game engine logic."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

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
    db.db_path = str(tmp_path / "test.db")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def manager(db):
    with patch("services.session_manager.ImageGenerator") as MockImgGen:
        instance = MockImgGen.return_value
        instance.generate_scene_image = AsyncMock(return_value="/images/scene.png")
        instance.generate_clue_image = AsyncMock(return_value="/images/clue.png")
        instance.generate_death_image = AsyncMock(return_value="/images/death.png")
        instance.generate_victory_image = AsyncMock(return_value="/images/victory.png")

        with patch.dict("os.environ", {"GOOGLE_API_KEY": "fake-key"}):
            mgr = SessionManager(db)
            mgr.image_gen = instance
            yield mgr


class TestGetOrCreate:
    @pytest.mark.asyncio
    async def test_creates_new_state(self, manager):
        state = await manager.get_or_create("new-1", Scenario.LAST_TRAIN)
        assert isinstance(state, GameState)
        assert state.session_id == "new-1"
        assert state.scenario == Scenario.LAST_TRAIN
        assert state.current_loop == 1

    @pytest.mark.asyncio
    async def test_returns_cached_state(self, manager):
        s1 = await manager.get_or_create("cached-1", Scenario.DINNER_PARTY)
        s2 = await manager.get_or_create("cached-1", Scenario.DINNER_PARTY)
        assert s1 is s2  # same object in memory

    @pytest.mark.asyncio
    async def test_scenario_config_applied(self, manager):
        state = await manager.get_or_create("cfg-1", Scenario.LOCKED_ROOM)
        assert state.loop_duration_seconds == 300
        assert len(state.characters) > 0

    @pytest.mark.asyncio
    async def test_persists_to_db(self, manager, db):
        await manager.get_or_create("persist-1", Scenario.THE_SIGNAL)
        result = await db.get_session("persist-1")
        assert result is not None
        assert result["scenario"] == "the_signal"


class TestStartGame:
    @pytest.mark.asyncio
    async def test_sends_game_state_to_client(self, manager):
        ws = AsyncMock()
        ws.send_json = AsyncMock()

        await manager.start_game("start-1", Scenario.DINNER_PARTY, ws)

        # Should have sent at least game_state and audio_cue
        calls = ws.send_json.call_args_list
        types_sent = [c[0][0]["type"] for c in calls]
        assert "game_state" in types_sent
        assert "audio_cue" in types_sent

    @pytest.mark.asyncio
    async def test_creates_clue_detector(self, manager):
        ws = AsyncMock()
        await manager.start_game("det-1", Scenario.LAST_TRAIN, ws)
        assert "det-1" in manager.clue_detectors

    @pytest.mark.asyncio
    async def test_stores_websocket(self, manager):
        ws = AsyncMock()
        await manager.start_game("ws-1", Scenario.LOCKED_ROOM, ws)
        assert manager.websockets["ws-1"] is ws


class TestBuildSystemPrompt:
    @pytest.mark.asyncio
    async def test_first_loop_prompt(self, manager):
        state = await manager.get_or_create("prompt-1", Scenario.DINNER_PARTY)
        prompt = manager._build_system_prompt(state)
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "first loop" in prompt.lower() or "Loop 1" in prompt or "no clues" in prompt.lower()

    @pytest.mark.asyncio
    async def test_prompt_includes_loop_history(self, manager):
        state = await manager.get_or_create("prompt-2", Scenario.LAST_TRAIN)
        state.loop_history = [
            LoopEntry(
                loop_number=1,
                status=LoopStatus.FAILED,
                death_description="Timer expired",
                actions_taken=["examined the briefcase"],
            )
        ]
        state.current_loop = 2

        prompt = manager._build_system_prompt(state)
        assert "Timer expired" in prompt or "timer expired" in prompt
        assert "examined the briefcase" in prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_found_clues(self, manager):
        state = await manager.get_or_create("prompt-3", Scenario.DINNER_PARTY)
        state.clues = [
            Clue(text="The Almond Scent", detail="Bitter almonds", is_key_clue=True, loop_discovered=1)
        ]

        prompt = manager._build_system_prompt(state)
        assert "Almond Scent" in prompt
        assert "[KEY]" in prompt

    @pytest.mark.asyncio
    async def test_prompt_shows_can_break_status(self, manager):
        state = await manager.get_or_create("prompt-4", Scenario.LOCKED_ROOM)
        state.can_break_loop = True

        prompt = manager._build_system_prompt(state)
        assert "Yes" in prompt  # can_break = "Yes"


class TestHandleLoopFail:
    @pytest.mark.asyncio
    async def test_sets_failed_status(self, manager):
        state = await manager.get_or_create("fail-1", Scenario.DINNER_PARTY)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time() - 60

        ws = AsyncMock()
        manager.websockets["fail-1"] = ws

        await manager._handle_loop_fail("fail-1", "Drank the poison wine")

        assert state.loop_status == LoopStatus.FAILED

    @pytest.mark.asyncio
    async def test_increments_loop_counter(self, manager):
        state = await manager.get_or_create("fail-2", Scenario.LAST_TRAIN)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time()
        assert state.current_loop == 1

        ws = AsyncMock()
        manager.websockets["fail-2"] = ws

        await manager._handle_loop_fail("fail-2", "Time ran out")
        assert state.current_loop == 2

    @pytest.mark.asyncio
    async def test_creates_loop_entry(self, manager):
        state = await manager.get_or_create("fail-3", Scenario.LOCKED_ROOM)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time() - 120

        ws = AsyncMock()
        manager.websockets["fail-3"] = ws

        await manager._handle_loop_fail("fail-3", "The room collapsed")

        assert len(state.loop_history) == 1
        entry = state.loop_history[0]
        assert entry.status == LoopStatus.FAILED
        assert entry.death_description == "The room collapsed"
        assert entry.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_sends_loop_failed_message(self, manager):
        state = await manager.get_or_create("fail-4", Scenario.THE_SIGNAL)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time()

        ws = AsyncMock()
        manager.websockets["fail-4"] = ws

        await manager._handle_loop_fail("fail-4", "Alien absorbed you")

        # Find the loop_failed message
        loop_failed_calls = [
            c for c in ws.send_json.call_args_list
            if c[0][0].get("type") == "loop_failed"
        ]
        assert len(loop_failed_calls) == 1
        data = loop_failed_calls[0][0][0]["data"]
        assert data["death_description"] == "Alien absorbed you"

    @pytest.mark.asyncio
    async def test_no_double_fail(self, manager):
        """Failing an already-failed loop should be a no-op."""
        state = await manager.get_or_create("fail-5", Scenario.DINNER_PARTY)
        state.loop_status = LoopStatus.FAILED  # already failed

        ws = AsyncMock()
        manager.websockets["fail-5"] = ws

        await manager._handle_loop_fail("fail-5", "Should not happen")
        # Should not create another entry or send messages
        ws.send_json.assert_not_called()


class TestHandleLoopBreak:
    @pytest.mark.asyncio
    async def test_sets_broken_status(self, manager):
        state = await manager.get_or_create("break-1", Scenario.DINNER_PARTY)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time()
        state.can_break_loop = True

        ws = AsyncMock()
        manager.websockets["break-1"] = ws

        await manager._handle_loop_break("break-1")

        assert state.loop_status == LoopStatus.BROKEN
        assert state.is_complete is True

    @pytest.mark.asyncio
    async def test_sends_loop_broken_message(self, manager):
        state = await manager.get_or_create("break-2", Scenario.LAST_TRAIN)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time()

        ws = AsyncMock()
        manager.websockets["break-2"] = ws

        await manager._handle_loop_break("break-2")

        broken_calls = [
            c for c in ws.send_json.call_args_list
            if c[0][0].get("type") == "loop_broken"
        ]
        assert len(broken_calls) == 1

    @pytest.mark.asyncio
    async def test_creates_broken_loop_entry(self, manager):
        state = await manager.get_or_create("break-3", Scenario.LOCKED_ROOM)
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time() - 200

        ws = AsyncMock()
        manager.websockets["break-3"] = ws

        await manager._handle_loop_break("break-3")

        assert len(state.loop_history) == 1
        assert state.loop_history[0].status == LoopStatus.BROKEN


class TestCleanTranscript:
    def test_removes_thinking_markers(self):
        text = "**Crafting the response**\nI'm planning the scene.\n\nThe rain falls heavily."
        result = SessionManager._clean_transcript(text)
        assert "rain falls" in result

    def test_removes_internal_reasoning(self):
        text = "I need to describe the scene.\nLet me think about this.\nThe door creaked open slowly."
        result = SessionManager._clean_transcript(text)
        assert "I need to" not in result
        assert "Let me think" not in result
        assert "door creaked" in result

    def test_preserves_clean_text(self):
        text = "The chandelier swayed gently above the long mahogany table."
        result = SessionManager._clean_transcript(text)
        assert result == text

    def test_empty_input(self):
        assert SessionManager._clean_transcript("") == ""
        assert SessionManager._clean_transcript(None) is None

    def test_all_thinking_fallback(self):
        """If everything is thinking text, tries regex fallback."""
        text = "**Planning** I should describe the scene."
        result = SessionManager._clean_transcript(text)
        # Should attempt to return something
        assert isinstance(result, str)

    def test_mixed_content(self):
        text = """**Setting the scene**
I'm focusing on atmosphere.

The clock strikes midnight. A chill runs through the room.
Everyone looks up from their plates."""
        result = SessionManager._clean_transcript(text)
        assert "clock strikes midnight" in result
        assert "Setting the scene" not in result


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_cleanup_on_disconnect(self, manager):
        state = await manager.get_or_create("disc-1", Scenario.DINNER_PARTY)
        ws = AsyncMock()
        manager.websockets["disc-1"] = ws

        await manager.disconnect("disc-1")

        assert "disc-1" not in manager.websockets
        assert "disc-1" not in manager.live_sessions
        assert "disc-1" not in manager.clue_detectors

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_no_error(self, manager):
        """Disconnecting unknown session should not raise."""
        await manager.disconnect("ghost-session")
