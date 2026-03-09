"""Tests for REST API endpoints."""

import json
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ["GOOGLE_API_KEY"] = "test-key-fake"

from main import app
from services.world_db import WorldDB


@pytest_asyncio.fixture
async def client(tmp_path):
    """Async client with isolated DB."""
    db = WorldDB()
    db.db_path = str(tmp_path / "api_test.db")
    await db.initialize()
    app.state.db = db

    from services.session_manager import SessionManager
    from unittest.mock import patch
    with patch("services.session_manager.ImageGenerator"):
        app.state.session_manager = SessionManager(db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await db.close()


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "echoes"


class TestScenariosAPI:
    @pytest.mark.asyncio
    async def test_list_scenarios(self, client):
        resp = await client.get("/api/scenarios/")
        assert resp.status_code == 200
        data = resp.json()
        assert "scenarios" in data
        assert len(data["scenarios"]) == 4

    @pytest.mark.asyncio
    async def test_list_scenarios_has_required_fields(self, client):
        resp = await client.get("/api/scenarios/")
        data = resp.json()
        for s in data["scenarios"]:
            assert "id" in s
            assert "name" in s
            assert "description" in s

    @pytest.mark.asyncio
    async def test_get_specific_scenario(self, client):
        resp = await client.get("/api/scenarios/last_train")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "last_train"
        assert data["name"] == "The Last Train"
        assert "characters" in data
        assert isinstance(data["characters"], list)

    @pytest.mark.asyncio
    async def test_get_scenario_dinner_party(self, client):
        resp = await client.get("/api/scenarios/dinner_party")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "dinner_party"
        assert data["loop_duration_seconds"] > 0
        assert data["total_clues"] > 0

    @pytest.mark.asyncio
    async def test_get_invalid_scenario_returns_error(self, client):
        with pytest.raises((ValueError, Exception)):
            await client.get("/api/scenarios/nonexistent")

    @pytest.mark.asyncio
    async def test_scenario_characters_have_names(self, client):
        resp = await client.get("/api/scenarios/locked_room")
        data = resp.json()
        for char in data["characters"]:
            assert "name" in char
            assert char["name"]  # non-empty


class TestSessionsAPI:
    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, client):
        resp = await client.get("/api/sessions/")
        assert resp.status_code == 200
        assert resp.json()["sessions"] == []

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, client):
        resp = await client.get("/api/sessions/ghost-id")
        assert resp.status_code == 404
        assert "error" in resp.json()

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, client):
        """Create via DB, list, get, delete."""
        db: WorldDB = app.state.db
        await db.save_session("life-1", "last_train", {"current_loop": 1})

        # List
        resp = await client.get("/api/sessions/")
        assert len(resp.json()["sessions"]) == 1

        # Get
        resp = await client.get("/api/sessions/life-1")
        assert resp.status_code == 200
        assert resp.json()["session"]["scenario"] == "last_train"

        # Delete
        resp = await client.delete("/api/sessions/life-1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify gone
        resp = await client.get("/api/sessions/life-1")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, client):
        resp = await client.delete("/api/sessions/no-exist")
        assert resp.status_code == 200  # idempotent delete


class TestExportAPI:
    @pytest.mark.asyncio
    async def test_export_nonexistent_session(self, client):
        resp = await client.get("/api/export/no-exist")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_export_existing_session(self, client):
        db: WorldDB = app.state.db
        game_state = {
            "session_id": "exp-1",
            "scenario": "dinner_party",
            "current_loop": 3,
            "clues": [
                {"id": "c1", "text": "Clue 1", "detail": "Detail", "is_key_clue": True, "loop_discovered": 1, "image_url": None}
            ],
            "loop_history": [
                {"loop_number": 1, "status": "failed", "death_description": "Time up", "duration_seconds": 300,
                 "summary": "", "actions_taken": [], "clues_found": [], "scene_image_url": None, "death_image_url": None}
            ],
            "characters": [{"name": "Julian", "role": "Guest", "description": "Nervous", "portrait_url": None, "voice_style": "neutral"}],
            "is_complete": False,
        }
        await db.save_session("exp-1", "dinner_party", game_state)

        resp = await client.get("/api/export/exp-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "exp-1"
        assert data["scenario"] == "dinner_party"
        assert data["export_ready"] is True
        assert len(data["clues"]) == 1
        assert len(data["loop_history"]) == 1
        assert len(data["characters"]) == 1
