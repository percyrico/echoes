"""Tests for Pydantic models and enums."""

import pytest
from datetime import datetime

from models.schemas import (
    Scenario, LoopStatus, Mood, Clue, CharacterProfile,
    LoopEntry, GameState, AudioCue,
)


class TestEnums:
    def test_scenario_values(self):
        assert Scenario.LAST_TRAIN.value == "last_train"
        assert Scenario.LOCKED_ROOM.value == "locked_room"
        assert Scenario.DINNER_PARTY.value == "dinner_party"
        assert Scenario.THE_SIGNAL.value == "the_signal"

    def test_scenario_from_string(self):
        assert Scenario("last_train") == Scenario.LAST_TRAIN
        assert Scenario("the_signal") == Scenario.THE_SIGNAL

    def test_scenario_invalid_raises(self):
        with pytest.raises(ValueError):
            Scenario("nonexistent_scenario")

    def test_loop_status_values(self):
        assert LoopStatus.ACTIVE.value == "active"
        assert LoopStatus.FAILED.value == "failed"
        assert LoopStatus.BROKEN.value == "broken"

    def test_mood_values(self):
        all_moods = {"tense", "calm", "urgent", "mysterious", "dread", "revelation"}
        assert {m.value for m in Mood} == all_moods

    def test_mood_from_string(self):
        assert Mood("tense") == Mood.TENSE
        assert Mood("revelation") == Mood.REVELATION


class TestClue:
    def test_clue_auto_id(self):
        clue = Clue(text="Test Clue")
        assert len(clue.id) == 8
        assert isinstance(clue.id, str)

    def test_clue_unique_ids(self):
        clues = [Clue(text=f"Clue {i}") for i in range(20)]
        ids = {c.id for c in clues}
        assert len(ids) == 20  # all unique

    def test_clue_defaults(self):
        clue = Clue(text="Found something")
        assert clue.detail == ""
        assert clue.loop_discovered == 1
        assert clue.image_url is None
        assert clue.is_key_clue is False

    def test_clue_full_construction(self):
        clue = Clue(
            id="abc12345",
            text="The Poison Vial",
            detail="Hidden in Julian's coat pocket",
            loop_discovered=3,
            image_url="/images/vial.png",
            is_key_clue=True,
        )
        assert clue.id == "abc12345"
        assert clue.is_key_clue is True
        assert clue.loop_discovered == 3

    def test_clue_serialization(self):
        clue = Clue(text="Test", detail="Detail", is_key_clue=True)
        data = clue.model_dump(mode="json")
        assert isinstance(data, dict)
        assert data["text"] == "Test"
        assert data["is_key_clue"] is True

        # Round-trip
        restored = Clue(**data)
        assert restored.text == clue.text
        assert restored.id == clue.id


class TestCharacterProfile:
    def test_character_defaults(self):
        char = CharacterProfile(name="Inspector")
        assert char.role == ""
        assert char.description == ""
        assert char.portrait_url is None
        assert char.voice_style == "neutral"

    def test_character_full(self):
        char = CharacterProfile(
            name="Countess Isabelle",
            role="Host",
            description="Elegant and cunning",
            portrait_url="/images/countess.png",
            voice_style="aristocratic",
        )
        assert char.name == "Countess Isabelle"
        assert char.voice_style == "aristocratic"


class TestLoopEntry:
    def test_loop_entry_defaults(self):
        entry = LoopEntry(loop_number=1)
        assert entry.summary == ""
        assert entry.actions_taken == []
        assert entry.clues_found == []
        assert entry.duration_seconds == 0
        assert entry.status == LoopStatus.FAILED
        assert entry.death_description == ""

    def test_loop_entry_failed(self):
        entry = LoopEntry(
            loop_number=2,
            summary="Drank the poisoned wine",
            actions_taken=["talked to Julian", "drank wine"],
            clues_found=["clue-001"],
            duration_seconds=187.5,
            status=LoopStatus.FAILED,
            death_description="The wine was laced with cyanide.",
        )
        assert entry.loop_number == 2
        assert len(entry.actions_taken) == 2
        assert entry.status == LoopStatus.FAILED

    def test_loop_entry_broken(self):
        entry = LoopEntry(
            loop_number=5,
            status=LoopStatus.BROKEN,
            summary="Accused Julian with evidence",
            duration_seconds=240,
        )
        assert entry.status == LoopStatus.BROKEN

    def test_loop_entry_mutable_lists(self):
        """Ensure each entry gets its own list instances."""
        e1 = LoopEntry(loop_number=1)
        e2 = LoopEntry(loop_number=2)
        e1.actions_taken.append("action")
        assert e1.actions_taken == ["action"]
        assert e2.actions_taken == []  # not shared


class TestGameState:
    def test_game_state_minimal(self):
        state = GameState(session_id="s1", scenario=Scenario.LAST_TRAIN)
        assert state.current_loop == 1
        assert state.loop_status == LoopStatus.ACTIVE
        assert state.loop_duration_seconds == 300
        assert state.clues == []
        assert state.loop_history == []
        assert state.characters == []
        assert state.current_mood == Mood.MYSTERIOUS
        assert state.total_clues_needed == 8
        assert state.can_break_loop is False
        assert state.is_complete is False
        assert isinstance(state.created_at, datetime)

    def test_game_state_to_dict(self, sample_game_state):
        d = sample_game_state.to_dict()
        assert isinstance(d, dict)
        assert d["session_id"] == "test-001"
        assert d["scenario"] == "dinner_party"
        assert d["current_loop"] == 1
        assert d["loop_status"] == "active"
        assert isinstance(d["characters"], list)
        assert len(d["characters"]) == 2

    def test_game_state_roundtrip(self, sample_game_state):
        d = sample_game_state.to_dict()
        restored = GameState(**d)
        assert restored.session_id == sample_game_state.session_id
        assert restored.scenario == sample_game_state.scenario
        assert restored.current_mood == sample_game_state.current_mood
        assert len(restored.characters) == len(sample_game_state.characters)

    def test_game_state_with_clues(self, sample_game_state, sample_clues):
        sample_game_state.clues = sample_clues
        d = sample_game_state.to_dict()
        assert len(d["clues"]) == 3
        assert d["clues"][0]["text"] == "The Almond Scent"

        restored = GameState(**d)
        assert len(restored.clues) == 3
        assert restored.clues[0].is_key_clue is True

    def test_game_state_with_loop_history(self, sample_game_state):
        sample_game_state.loop_history = [
            LoopEntry(loop_number=1, status=LoopStatus.FAILED, death_description="Timer ran out"),
            LoopEntry(loop_number=2, status=LoopStatus.FAILED, death_description="Drank poison"),
        ]
        sample_game_state.current_loop = 3

        d = sample_game_state.to_dict()
        assert len(d["loop_history"]) == 2
        assert d["current_loop"] == 3

        restored = GameState(**d)
        assert len(restored.loop_history) == 2
        assert restored.loop_history[1].death_description == "Drank poison"

    def test_game_state_can_break_loop_flag(self, sample_game_state, sample_clues):
        """Key clue counting doesn't auto-set can_break_loop — that's SessionManager's job."""
        sample_game_state.clues = sample_clues
        key_count = sum(1 for c in sample_game_state.clues if c.is_key_clue)
        assert key_count == 2
        # can_break_loop is still False because the game engine sets it
        assert sample_game_state.can_break_loop is False


class TestAudioCue:
    def test_audio_cue_defaults(self):
        cue = AudioCue(track="mysterious_pads")
        assert cue.volume == 0.12
        assert cue.fade_in_ms == 2000
        assert cue.fade_out_ms == 3000

    def test_audio_cue_custom(self):
        cue = AudioCue(track="urgent_pulse", volume=0.15, fade_in_ms=1500, fade_out_ms=2000)
        assert cue.track == "urgent_pulse"
        assert cue.volume == 0.15

    def test_audio_cue_serialization(self):
        cue = AudioCue(track="tense_drone", volume=0.1)
        d = cue.model_dump()
        assert d["track"] == "tense_drone"
        restored = AudioCue(**d)
        assert restored.track == cue.track
