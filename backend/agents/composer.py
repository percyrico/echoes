"""ComposerAgent — Maps scene mood to ambient audio cues for Echoes."""

from models.schemas import Mood, AudioCue

# Mood to ambient track mapping
MOOD_TRACKS = {
    Mood.TENSE: "tense_drone",
    Mood.CALM: "calm_ambient",
    Mood.URGENT: "urgent_pulse",
    Mood.MYSTERIOUS: "mysterious_pads",
    Mood.DREAD: "dread_low",
    Mood.REVELATION: "revelation_shimmer",
}

# Scenario-specific ambient overrides
SCENARIO_TRACKS = {
    "last_train": {
        Mood.TENSE: "last_train_rain",
        Mood.MYSTERIOUS: "last_train_rain",
        Mood.DREAD: "tense_drone",
        Mood.CALM: "calm_ambient",
    },
    "locked_room": {
        Mood.MYSTERIOUS: "locked_room_hum",
        Mood.TENSE: "locked_room_hum",
        Mood.DREAD: "dread_low",
        Mood.CALM: "calm_ambient",
    },
    "dinner_party": {
        Mood.CALM: "dinner_party_jazz",
        Mood.MYSTERIOUS: "dinner_party_jazz",
        Mood.TENSE: "tense_drone",
        Mood.URGENT: "urgent_pulse",
    },
    "the_signal": {
        Mood.DREAD: "signal_static",
        Mood.TENSE: "signal_static",
        Mood.MYSTERIOUS: "signal_static",
        Mood.URGENT: "urgent_pulse",
    },
    "the_crash": {
        Mood.TENSE: "tense_drone",
        Mood.DREAD: "dread_low",
        Mood.MYSTERIOUS: "mysterious_pads",
        Mood.URGENT: "urgent_pulse",
    },
    "the_heist": {
        Mood.TENSE: "tense_drone",
        Mood.URGENT: "urgent_pulse",
        Mood.MYSTERIOUS: "mysterious_pads",
        Mood.CALM: "calm_ambient",
    },
    "room_414": {
        Mood.DREAD: "dread_low",
        Mood.MYSTERIOUS: "mysterious_pads",
        Mood.TENSE: "tense_drone",
        Mood.CALM: "calm_ambient",
    },
    "the_factory": {
        Mood.TENSE: "tense_drone",
        Mood.DREAD: "dread_low",
        Mood.URGENT: "urgent_pulse",
        Mood.MYSTERIOUS: "mysterious_pads",
    },
}


def get_audio_cue(mood: Mood, scenario: str = "last_train") -> AudioCue:
    """Get the appropriate audio cue for a mood and scenario."""
    scenario_overrides = SCENARIO_TRACKS.get(scenario, {})
    track = scenario_overrides.get(mood, MOOD_TRACKS.get(mood, "calm_ambient"))

    # Keep ambient low so narrator voice is always clear
    if mood in (Mood.TENSE, Mood.URGENT):
        volume = 0.15
        fade_in = 1500
    elif mood in (Mood.DREAD,):
        volume = 0.08
        fade_in = 3000
    elif mood == Mood.REVELATION:
        volume = 0.14
        fade_in = 1000
    else:
        volume = 0.10
        fade_in = 2000

    return AudioCue(
        track=track,
        volume=volume,
        fade_in_ms=fade_in,
        fade_out_ms=3000,
    )
