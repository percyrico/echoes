"""Tests for ClueDetector — transcript analysis and JSON parsing."""

import pytest

from models.schemas import Scenario, GameState, Mood, Clue
from services.clue_detector import ClueDetector


class TestExtractClueDefinitions:
    def test_extracts_from_system_prompt(self):
        detector = ClueDetector.__new__(ClueDetector)
        detector.scenario = Scenario.DINNER_PARTY
        from models.scenarios import get_scenario_config
        detector.config = get_scenario_config(Scenario.DINNER_PARTY)
        result = detector._extract_clue_definitions()
        assert "CLUE" in result.upper()
        assert len(result) > 50

    @pytest.mark.parametrize("scenario", list(Scenario))
    def test_all_scenarios_have_clues(self, scenario):
        detector = ClueDetector.__new__(ClueDetector)
        detector.scenario = scenario
        from models.scenarios import get_scenario_config
        detector.config = get_scenario_config(scenario)
        result = detector._extract_clue_definitions()
        assert result != "No clue definitions found."


class TestParseResponse:
    @pytest.fixture
    def detector(self):
        det = ClueDetector.__new__(ClueDetector)
        det.scenario = Scenario.DINNER_PARTY
        from models.scenarios import get_scenario_config
        det.config = get_scenario_config(Scenario.DINNER_PARTY)
        return det

    @pytest.fixture
    def game_state(self):
        return GameState(
            session_id="test",
            scenario=Scenario.DINNER_PARTY,
            current_mood=Mood.MYSTERIOUS,
        )

    def test_parse_clean_json(self, detector, game_state):
        response = '{"new_clues": [], "mood": "tense", "should_fail": false, "can_break": false, "actions": ["looked around"]}'
        result = detector._parse_response(response, game_state)
        assert result["mood"] == "tense"
        assert result["should_fail"] is False
        assert result["actions"] == ["looked around"]

    def test_parse_json_with_code_fence(self, detector, game_state):
        response = '```json\n{"new_clues": [{"text": "The Scent", "detail": "Almonds", "is_key_clue": true}], "mood": "dread", "should_fail": false, "can_break": false, "actions": []}\n```'
        result = detector._parse_response(response, game_state)
        assert len(result["new_clues"]) == 1
        assert result["new_clues"][0]["text"] == "The Scent"
        assert result["mood"] == "dread"

    def test_parse_json_embedded_in_text(self, detector, game_state):
        response = 'Here is the analysis:\n{"new_clues": [], "mood": "calm", "should_fail": false, "can_break": false, "actions": []}\nEnd.'
        result = detector._parse_response(response, game_state)
        assert result["mood"] == "calm"

    def test_parse_invalid_json_returns_defaults(self, detector, game_state):
        response = "This is not JSON at all"
        result = detector._parse_response(response, game_state)
        assert result["new_clues"] == []
        assert result["mood"] == game_state.current_mood.value
        assert result["should_fail"] is False

    def test_parse_invalid_mood_uses_current(self, detector, game_state):
        response = '{"new_clues": [], "mood": "horrified", "should_fail": false, "actions": []}'
        result = detector._parse_response(response, game_state)
        assert result["mood"] == "mysterious"  # falls back to current

    def test_parse_with_clue_discovery(self, detector, game_state):
        response = '''{
            "new_clues": [
                {"text": "The Poison Vial", "detail": "Hidden in coat pocket", "is_key_clue": true},
                {"text": "Scratched Watch", "detail": "Time stopped at 9:47", "is_key_clue": false}
            ],
            "mood": "revelation",
            "should_fail": false,
            "can_break": false,
            "actions": ["searched Julian's coat", "examined the watch"]
        }'''
        result = detector._parse_response(response, game_state)
        assert len(result["new_clues"]) == 2
        assert result["new_clues"][0]["is_key_clue"] is True
        assert result["mood"] == "revelation"
        assert len(result["actions"]) == 2

    def test_parse_should_fail_true(self, detector, game_state):
        response = '{"new_clues": [], "mood": "dread", "should_fail": true, "can_break": false, "actions": ["drank the wine"]}'
        result = detector._parse_response(response, game_state)
        assert result["should_fail"] is True

    def test_parse_can_break_true(self, detector, game_state):
        game_state.can_break_loop = True
        response = '{"new_clues": [], "mood": "revelation", "should_fail": false, "can_break": true, "actions": ["accused Julian"]}'
        result = detector._parse_response(response, game_state)
        assert result["can_break"] is True

    def test_parse_missing_fields_use_defaults(self, detector, game_state):
        response = '{"new_clues": []}'
        result = detector._parse_response(response, game_state)
        assert result["mood"] == "mysterious"
        assert result["should_fail"] is False
        assert result["actions"] == []


class TestAnalyzeShortCircuit:
    """Test the early return for short/empty transcripts."""

    @pytest.mark.asyncio
    async def test_empty_transcript(self):
        det = ClueDetector.__new__(ClueDetector)
        det.scenario = Scenario.DINNER_PARTY
        from models.scenarios import get_scenario_config
        det.config = get_scenario_config(Scenario.DINNER_PARTY)

        state = GameState(session_id="t", scenario=Scenario.DINNER_PARTY)
        result = await det.analyze("", state)
        assert result["new_clues"] == []

    @pytest.mark.asyncio
    async def test_short_transcript(self):
        det = ClueDetector.__new__(ClueDetector)
        det.scenario = Scenario.DINNER_PARTY
        from models.scenarios import get_scenario_config
        det.config = get_scenario_config(Scenario.DINNER_PARTY)

        state = GameState(session_id="t", scenario=Scenario.DINNER_PARTY)
        result = await det.analyze("Hi", state)
        assert result["new_clues"] == []
