"""Echoes — Pydantic schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Scenario(str, Enum):
    LAST_TRAIN = "last_train"
    LOCKED_ROOM = "locked_room"
    DINNER_PARTY = "dinner_party"
    THE_SIGNAL = "the_signal"
    THE_CRASH = "the_crash"
    THE_HEIST = "the_heist"
    ROOM_414 = "room_414"
    THE_FACTORY = "the_factory"


class LoopStatus(str, Enum):
    ACTIVE = "active"
    FAILED = "failed"
    BROKEN = "broken"  # won


class Mood(str, Enum):
    TENSE = "tense"
    CALM = "calm"
    URGENT = "urgent"
    MYSTERIOUS = "mysterious"
    DREAD = "dread"
    REVELATION = "revelation"


class Clue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str
    detail: str = ""
    loop_discovered: int = 1
    image_url: Optional[str] = None
    is_key_clue: bool = False  # needed to break the loop


class CharacterProfile(BaseModel):
    name: str
    role: str = ""
    description: str = ""
    portrait_url: Optional[str] = None
    voice_style: str = "neutral"


class LoopEntry(BaseModel):
    loop_number: int
    summary: str = ""
    actions_taken: list[str] = Field(default_factory=list)
    clues_found: list[str] = Field(default_factory=list)  # clue IDs
    duration_seconds: float = 0
    status: LoopStatus = LoopStatus.FAILED
    death_description: str = ""
    scene_image_url: Optional[str] = None
    death_image_url: Optional[str] = None


class GameState(BaseModel):
    session_id: str
    scenario: Scenario
    current_loop: int = 1
    loop_status: LoopStatus = LoopStatus.ACTIVE
    loop_start_time: Optional[float] = None  # timestamp
    loop_duration_seconds: int = 300  # 5 minutes default
    clues: list[Clue] = Field(default_factory=list)
    loop_history: list[LoopEntry] = Field(default_factory=list)
    characters: list[CharacterProfile] = Field(default_factory=list)
    current_mood: Mood = Mood.MYSTERIOUS
    total_clues_needed: int = 8
    player_name: str = "Detective"
    can_break_loop: bool = False  # true when enough key clues found
    is_complete: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class AudioCue(BaseModel):
    track: str
    volume: float = 0.12
    fade_in_ms: int = 2000
    fade_out_ms: int = 3000
