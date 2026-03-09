"""Shared fixtures for Echoes backend tests."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from models.schemas import (
    Scenario, LoopStatus, Mood, Clue, CharacterProfile,
    LoopEntry, GameState, AudioCue,
)
from services.world_db import WorldDB


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def tmp_db(tmp_path):
    """Create an isolated WorldDB backed by a temp file."""
    db_path = str(tmp_path / "test_echoes.db")
    db = WorldDB()
    db.db_path = db_path
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def sample_game_state() -> GameState:
    return GameState(
        session_id="test-001",
        scenario=Scenario.DINNER_PARTY,
        current_loop=1,
        loop_status=LoopStatus.ACTIVE,
        loop_duration_seconds=300,
        total_clues_needed=8,
        characters=[
            CharacterProfile(name="Countess Isabelle", role="Host", description="Elegant, cunning"),
            CharacterProfile(name="Julian", role="Guest", description="Charming, nervous"),
        ],
        current_mood=Mood.MYSTERIOUS,
    )


@pytest.fixture
def sample_clues() -> list[Clue]:
    return [
        Clue(id="clue-001", text="The Almond Scent", detail="Faint bitter almonds near the soufflé", loop_discovered=1, is_key_clue=True),
        Clue(id="clue-002", text="Julian's Trembling Hand", detail="His hand shook when pouring wine", loop_discovered=1, is_key_clue=False),
        Clue(id="clue-003", text="The Switched Glass", detail="Julian swapped glasses mid-toast", loop_discovered=2, is_key_clue=True),
    ]


@pytest.fixture
def mock_image_gen():
    """Mock ImageGenerator that returns fake URLs."""
    with patch("services.session_manager.ImageGenerator") as MockImgGen:
        instance = MockImgGen.return_value
        instance.generate_scene_image = AsyncMock(return_value="/images/test-scene.png")
        instance.generate_clue_image = AsyncMock(return_value="/images/test-clue.png")
        instance.generate_death_image = AsyncMock(return_value="/images/test-death.png")
        instance.generate_victory_image = AsyncMock(return_value="/images/test-victory.png")
        yield instance


@pytest.fixture
def app_client():
    """Synchronous test client for HTTP endpoint tests."""
    os.environ["GOOGLE_API_KEY"] = "test-key-fake"
    from main import app
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def async_app_client():
    """Async test client for HTTP endpoint tests."""
    os.environ["GOOGLE_API_KEY"] = "test-key-fake"
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
