"""Tests for WebSocket game endpoint."""

import asyncio
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

os.environ["GOOGLE_API_KEY"] = "test-key-fake"

from main import app
from services.world_db import WorldDB
from services.session_manager import SessionManager


@pytest_asyncio.fixture
async def setup_app(tmp_path):
    """Set up app with isolated DB and mocked external services."""
    db = WorldDB()
    db.db_path = str(tmp_path / "ws_test.db")
    await db.initialize()
    app.state.db = db

    with patch("services.session_manager.ImageGenerator") as MockImgGen:
        instance = MockImgGen.return_value
        instance.generate_scene_image = AsyncMock(return_value="/images/scene.png")
        instance.generate_clue_image = AsyncMock(return_value=None)
        instance.generate_death_image = AsyncMock(return_value=None)
        instance.generate_victory_image = AsyncMock(return_value=None)

        mgr = SessionManager(db)
        mgr.image_gen = instance
        app.state.session_manager = mgr

        yield app

    await db.close()


class TestWebSocketConnection:
    @pytest.mark.asyncio
    async def test_websocket_accepts_connection(self, setup_app):
        with TestClient(setup_app) as client:
            with client.websocket_connect("/ws/game/test-ws-1") as ws:
                # Connection should be accepted
                assert ws is not None

    @pytest.mark.asyncio
    async def test_start_game_sends_state(self, setup_app):
        """Starting a game should send game_state and audio_cue messages."""
        with TestClient(setup_app) as client:
            with client.websocket_connect("/ws/game/test-ws-2") as ws:
                # Mock start_loop to not actually connect to Gemini
                mgr: SessionManager = setup_app.state.session_manager
                original_start_loop = mgr.start_loop
                mgr.start_loop = AsyncMock()

                ws.send_json({"type": "start_game", "scenario": "dinner_party"})

                # Should receive game_state
                msg1 = ws.receive_json()
                assert msg1["type"] == "game_state"
                assert msg1["data"]["scenario"] == "dinner_party"
                assert msg1["data"]["current_loop"] == 1

                # Should receive audio_cue
                msg2 = ws.receive_json()
                assert msg2["type"] == "audio_cue"
                assert "track" in msg2["data"]

                mgr.start_loop = original_start_loop

    @pytest.mark.asyncio
    async def test_start_game_all_scenarios(self, setup_app):
        """Each scenario should produce valid game state."""
        scenarios = ["last_train", "locked_room", "dinner_party", "the_signal"]

        for i, scenario in enumerate(scenarios):
            with TestClient(setup_app) as client:
                with client.websocket_connect(f"/ws/game/test-all-{i}") as ws:
                    mgr: SessionManager = setup_app.state.session_manager
                    mgr.start_loop = AsyncMock()

                    ws.send_json({"type": "start_game", "scenario": scenario})

                    msg = ws.receive_json()
                    assert msg["type"] == "game_state"
                    assert msg["data"]["scenario"] == scenario

    @pytest.mark.asyncio
    async def test_user_text_forwarded(self, setup_app):
        """User text should be forwarded to the session manager."""
        with TestClient(setup_app) as client:
            with client.websocket_connect("/ws/game/test-text-1") as ws:
                mgr: SessionManager = setup_app.state.session_manager
                mgr.start_loop = AsyncMock()
                mgr.handle_text_input = AsyncMock()

                ws.send_json({"type": "start_game", "scenario": "last_train"})
                ws.receive_json()  # game_state
                ws.receive_json()  # audio_cue

                ws.send_json({"type": "user_text", "text": "I look around the train car"})

                # Give async task time to process
                await asyncio.sleep(0.1)
                mgr.handle_text_input.assert_called_once()
                call_args = mgr.handle_text_input.call_args
                assert call_args[0][1] == "I look around the train car"

    @pytest.mark.asyncio
    async def test_binary_audio_forwarded(self, setup_app):
        """Binary audio frames with 0x01 prefix should be forwarded."""
        with TestClient(setup_app) as client:
            with client.websocket_connect("/ws/game/test-audio-1") as ws:
                mgr: SessionManager = setup_app.state.session_manager
                mgr.start_loop = AsyncMock()
                mgr.handle_audio = AsyncMock()

                ws.send_json({"type": "start_game", "scenario": "locked_room"})
                ws.receive_json()  # game_state
                ws.receive_json()  # audio_cue

                # Send binary audio with 0x01 prefix
                audio_data = bytes([0x01]) + b"\x00\x01\x02\x03" * 100
                ws.send_bytes(audio_data)

                await asyncio.sleep(0.1)
                mgr.handle_audio.assert_called_once()
                # Payload should not include the 0x01 prefix byte
                sent_audio = mgr.handle_audio.call_args[0][1]
                assert sent_audio == b"\x00\x01\x02\x03" * 100

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, setup_app):
        """Disconnecting should clean up session resources."""
        mgr: SessionManager = setup_app.state.session_manager
        mgr.start_loop = AsyncMock()

        with TestClient(setup_app) as client:
            with client.websocket_connect("/ws/game/test-disc-1") as ws:
                ws.send_json({"type": "start_game", "scenario": "the_signal"})
                ws.receive_json()
                ws.receive_json()

        # After disconnect, session should be cleaned from websockets dict
        await asyncio.sleep(0.2)
        assert "test-disc-1" not in mgr.websockets


class TestWebSocketGameFlow:
    @pytest.mark.asyncio
    async def test_game_state_structure(self, setup_app):
        """Verify the game_state message has all required fields."""
        with TestClient(setup_app) as client:
            with client.websocket_connect("/ws/game/test-struct-1") as ws:
                mgr: SessionManager = setup_app.state.session_manager
                mgr.start_loop = AsyncMock()

                ws.send_json({"type": "start_game", "scenario": "dinner_party"})
                msg = ws.receive_json()

                state = msg["data"]
                required = [
                    "session_id", "scenario", "current_loop", "loop_status",
                    "loop_duration_seconds", "clues", "loop_history",
                    "characters", "current_mood", "total_clues_needed",
                    "can_break_loop", "is_complete",
                ]
                for key in required:
                    assert key in state, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_audio_cue_structure(self, setup_app):
        """Verify audio_cue message structure."""
        with TestClient(setup_app) as client:
            with client.websocket_connect("/ws/game/test-audio-struct") as ws:
                mgr: SessionManager = setup_app.state.session_manager
                mgr.start_loop = AsyncMock()

                ws.send_json({"type": "start_game", "scenario": "last_train"})
                ws.receive_json()  # game_state
                msg = ws.receive_json()  # audio_cue

                assert msg["type"] == "audio_cue"
                cue = msg["data"]
                assert "track" in cue
                assert "volume" in cue
                assert "fade_in_ms" in cue
                assert "fade_out_ms" in cue
                assert 0 < cue["volume"] <= 1.0
