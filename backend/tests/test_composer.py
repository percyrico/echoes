"""Tests for the audio composer agent."""

import pytest

from models.schemas import Mood, AudioCue
from agents.composer import get_audio_cue, MOOD_TRACKS, SCENARIO_TRACKS


class TestGetAudioCue:
    @pytest.mark.parametrize("mood", list(Mood))
    def test_returns_audio_cue_for_all_moods(self, mood):
        cue = get_audio_cue(mood)
        assert isinstance(cue, AudioCue)
        assert cue.track  # non-empty
        assert 0 < cue.volume <= 1.0
        assert cue.fade_in_ms > 0
        assert cue.fade_out_ms > 0

    @pytest.mark.parametrize("scenario", ["last_train", "locked_room", "dinner_party", "the_signal"])
    @pytest.mark.parametrize("mood", list(Mood))
    def test_all_scenario_mood_combos(self, scenario, mood):
        cue = get_audio_cue(mood, scenario)
        assert isinstance(cue, AudioCue)
        assert cue.track  # always returns something

    def test_scenario_overrides_take_priority(self):
        # last_train + TENSE should use "last_train_rain", not default "tense_drone"
        cue = get_audio_cue(Mood.TENSE, "last_train")
        assert cue.track == "last_train_rain"

    def test_fallback_to_default_track(self):
        # For a mood not in scenario overrides, uses MOOD_TRACKS default
        cue = get_audio_cue(Mood.REVELATION, "last_train")
        assert cue.track == "revelation_shimmer"

    def test_unknown_scenario_uses_defaults(self):
        cue = get_audio_cue(Mood.TENSE, "nonexistent_scenario")
        assert cue.track == MOOD_TRACKS[Mood.TENSE]

    def test_tense_urgent_higher_volume(self):
        tense = get_audio_cue(Mood.TENSE)
        calm = get_audio_cue(Mood.CALM)
        assert tense.volume > calm.volume

    def test_dread_lowest_volume(self):
        dread = get_audio_cue(Mood.DREAD)
        assert dread.volume == 0.08

    def test_dread_slowest_fade_in(self):
        dread = get_audio_cue(Mood.DREAD)
        tense = get_audio_cue(Mood.TENSE)
        assert dread.fade_in_ms > tense.fade_in_ms

    def test_revelation_fast_fade_in(self):
        rev = get_audio_cue(Mood.REVELATION)
        assert rev.fade_in_ms == 1000

    def test_dinner_party_jazz_for_calm(self):
        cue = get_audio_cue(Mood.CALM, "dinner_party")
        assert cue.track == "dinner_party_jazz"

    def test_signal_static_for_dread(self):
        cue = get_audio_cue(Mood.DREAD, "the_signal")
        assert cue.track == "signal_static"

    def test_locked_room_hum_for_mysterious(self):
        cue = get_audio_cue(Mood.MYSTERIOUS, "locked_room")
        assert cue.track == "locked_room_hum"


class TestMoodTracksComplete:
    def test_all_moods_have_default_track(self):
        for mood in Mood:
            assert mood in MOOD_TRACKS, f"Missing default track for {mood}"

    def test_no_empty_tracks(self):
        for mood, track in MOOD_TRACKS.items():
            assert track, f"Empty track for {mood}"
