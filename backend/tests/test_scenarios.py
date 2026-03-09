"""Tests for scenario configs."""

import pytest

from models.schemas import Scenario, Mood, CharacterProfile
from models.scenarios import get_scenario_config, get_all_scenarios


class TestGetScenarioConfig:
    @pytest.mark.parametrize("scenario", list(Scenario))
    def test_every_scenario_has_config(self, scenario):
        config = get_scenario_config(scenario)
        assert isinstance(config, dict)

    @pytest.mark.parametrize("scenario", list(Scenario))
    def test_required_keys_present(self, scenario):
        config = get_scenario_config(scenario)
        required_keys = [
            "name", "description", "difficulty", "loop_duration_seconds",
            "total_clues", "ambient_track", "initial_mood", "art_direction",
            "characters", "opening_narration", "system_prompt",
        ]
        for key in required_keys:
            assert key in config, f"Missing key '{key}' in {scenario.value}"

    @pytest.mark.parametrize("scenario", list(Scenario))
    def test_initial_mood_is_valid(self, scenario):
        config = get_scenario_config(scenario)
        assert isinstance(config["initial_mood"], Mood)

    @pytest.mark.parametrize("scenario", list(Scenario))
    def test_characters_are_profiles(self, scenario):
        config = get_scenario_config(scenario)
        chars = config["characters"]
        assert isinstance(chars, list)
        assert len(chars) >= 1
        for c in chars:
            assert isinstance(c, CharacterProfile)
            assert c.name  # non-empty

    @pytest.mark.parametrize("scenario", list(Scenario))
    def test_system_prompt_has_clue_section(self, scenario):
        config = get_scenario_config(scenario)
        prompt = config["system_prompt"]
        assert "CLUE" in prompt.upper(), f"{scenario.value} system prompt missing CLUE section"

    @pytest.mark.parametrize("scenario", list(Scenario))
    def test_system_prompt_has_template_vars(self, scenario):
        config = get_scenario_config(scenario)
        prompt = config["system_prompt"]
        # Must contain template variables for dynamic context
        assert "{loop_history}" in prompt or "{current_loop}" in prompt, \
            f"{scenario.value} system prompt missing template variables"

    @pytest.mark.parametrize("scenario", list(Scenario))
    def test_loop_duration_reasonable(self, scenario):
        config = get_scenario_config(scenario)
        duration = config["loop_duration_seconds"]
        assert 60 <= duration <= 600, f"{scenario.value} has unreasonable duration: {duration}"

    @pytest.mark.parametrize("scenario", list(Scenario))
    def test_total_clues_reasonable(self, scenario):
        config = get_scenario_config(scenario)
        total = config["total_clues"]
        assert 4 <= total <= 20, f"{scenario.value} has unreasonable clue count: {total}"


class TestGetAllScenarios:
    def test_returns_list(self):
        result = get_all_scenarios()
        assert isinstance(result, list)

    def test_returns_all_four(self):
        result = get_all_scenarios()
        assert len(result) == 4

    def test_summary_keys(self):
        result = get_all_scenarios()
        for item in result:
            assert "id" in item
            assert "name" in item
            assert "description" in item

    def test_no_system_prompt_leaked(self):
        """Summary should NOT include the full system prompt."""
        result = get_all_scenarios()
        for item in result:
            assert "system_prompt" not in item

    def test_scenario_ids_match_enum(self):
        result = get_all_scenarios()
        ids = {item["id"] for item in result}
        expected = {s.value for s in Scenario}
        assert ids == expected
