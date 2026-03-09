"""Scenario listing endpoints."""

from fastapi import APIRouter

from models.schemas import Scenario
from models.scenarios import get_all_scenarios, get_scenario_config

router = APIRouter()


@router.get("/")
async def list_scenarios():
    """List all available scenarios."""
    return {"scenarios": get_all_scenarios()}


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get details for a specific scenario."""
    scenario = Scenario(scenario_id)
    config = get_scenario_config(scenario)
    return {
        "id": scenario.value,
        "name": config["name"],
        "description": config["description"],
        "difficulty": config["difficulty"],
        "loop_duration_seconds": config["loop_duration_seconds"],
        "total_clues": config["total_clues"],
        "initial_mood": config["initial_mood"].value,
        "ambient_track": config["ambient_track"],
        "art_direction": config["art_direction"],
        "characters": [c.model_dump() for c in config["characters"]],
    }
