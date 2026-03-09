"""ClueDetector — Analyzes narrator transcripts to detect clue discoveries and mood."""

import json
import re
from typing import Optional

from google import genai
from google.genai import types

from models.schemas import Scenario, GameState, Mood, Clue
from models.scenarios import get_scenario_config


class ClueDetector:
    """Uses gemini-2.5-flash-lite to analyze transcript chunks for clue triggers."""

    def __init__(self, scenario: Scenario, api_key: str):
        self.scenario = scenario
        self.config = get_scenario_config(scenario)
        self.client = genai.Client(api_key=api_key)
        self._clue_definitions = self._extract_clue_definitions()

    def _extract_clue_definitions(self) -> str:
        """Extract clue definitions from the scenario system prompt for analysis."""
        prompt = self.config["system_prompt"]
        # Find the CLUE SYSTEM section
        clue_start = prompt.find("CLUE SYSTEM")
        if clue_start == -1:
            clue_start = prompt.find("Clue System")
        if clue_start == -1:
            return "No clue definitions found."

        # Find where clues end (RED HERRINGS section)
        clue_end = prompt.find("RED HERRING")
        if clue_end == -1:
            clue_end = prompt.find("LOOP FAILURE")
        if clue_end == -1:
            clue_end = clue_start + 3000

        return prompt[clue_start:clue_end].strip()

    async def analyze(self, transcript: str, game_state: GameState) -> dict:
        """Analyze a transcript chunk for clue discoveries and mood.

        Returns:
            {
                "new_clues": [{"text": str, "detail": str, "is_key_clue": bool}],
                "mood": "tense",
                "should_fail": false,
                "can_break": false,
                "actions": ["action description"]
            }
        """
        if not transcript or len(transcript.strip()) < 20:
            return {
                "new_clues": [],
                "mood": game_state.current_mood.value,
                "should_fail": False,
                "can_break": game_state.can_break_loop,
                "actions": [],
            }

        found_clue_texts = [c.text for c in game_state.clues]
        found_clues_str = "\n".join(f"- {t}" for t in found_clue_texts) if found_clue_texts else "None yet"

        key_clues_found = sum(1 for c in game_state.clues if c.is_key_clue)
        total_needed = game_state.total_clues_needed

        analysis_prompt = f"""You are analyzing a transcript from an interactive mystery game narrator. Determine if any NEW clues were revealed in this text.

SCENARIO: {self.config['name']}

CLUE DEFINITIONS:
{self._clue_definitions}

ALREADY FOUND CLUES:
{found_clues_str}

KEY CLUES FOUND: {key_clues_found} / {total_needed} needed to win

TRANSCRIPT TO ANALYZE:
\"\"\"{transcript}\"\"\"

Respond in JSON only:
{{
    "new_clues": [
        {{
            "text": "Short clue title (e.g., 'The Almond Scent')",
            "detail": "What was revealed in the transcript",
            "is_key_clue": true
        }}
    ],
    "mood": "tense|calm|urgent|mysterious|dread|revelation",
    "should_fail": false,
    "actions": ["Brief description of player/narrator actions in this chunk"],
    "can_break": false
}}

RULES:
- Only include clues that are NEWLY discovered in this transcript (not already found).
- Match clues against the CLUE DEFINITIONS above. Only count it if the information was actually revealed.
- Set "should_fail" to true ONLY if the transcript describes a fatal action (drinking poison, dying, etc.).
- Set "can_break" to true if the player now has enough key clues AND is attempting to solve/break the loop.
- Set mood based on the emotional tone of the transcript.
- Be conservative — don't invent clues that weren't actually in the text.
- If no new clues, return empty array for new_clues.
"""

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[{"role": "user", "parts": [{"text": analysis_prompt}]}],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=512,
                    thinking_config=types.ThinkingConfig(thinking_budget=512),
                ),
            )

            result = self._parse_response(response.text, game_state)
            return result

        except Exception as e:
            print(f"ClueDetector error: {e}")
            return {
                "new_clues": [],
                "mood": game_state.current_mood.value,
                "should_fail": False,
                "can_break": game_state.can_break_loop,
                "actions": [],
            }

    def _parse_response(self, response_text: str, game_state: GameState) -> dict:
        """Parse the LLM response into structured data."""
        try:
            text = response_text.strip()
            # Remove markdown code fences
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            # Try direct parse
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # Try to find JSON object
                match = re.search(r'\{', text)
                if match:
                    brace_count = 0
                    start = match.start()
                    end = start
                    for i in range(start, len(text)):
                        if text[i] == '{':
                            brace_count += 1
                        elif text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                    data = json.loads(text[start:end])
                else:
                    raise json.JSONDecodeError("No JSON", text, 0)

            # Validate mood
            mood_str = data.get("mood", game_state.current_mood.value)
            try:
                Mood(mood_str)
            except ValueError:
                mood_str = game_state.current_mood.value

            return {
                "new_clues": data.get("new_clues", []),
                "mood": mood_str,
                "should_fail": data.get("should_fail", False),
                "can_break": data.get("can_break", game_state.can_break_loop),
                "actions": data.get("actions", []),
            }

        except (json.JSONDecodeError, KeyError, IndexError):
            return {
                "new_clues": [],
                "mood": game_state.current_mood.value,
                "should_fail": False,
                "can_break": game_state.can_break_loop,
                "actions": [],
            }
