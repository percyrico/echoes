export type Scenario = "last_train" | "locked_room" | "dinner_party" | "the_signal" | "the_crash" | "the_heist" | "room_414" | "the_factory";
export type LoopStatus = "active" | "failed" | "broken";
export type Mood = "tense" | "calm" | "urgent" | "mysterious" | "dread" | "revelation";

export interface Clue {
  id: string;
  text: string;
  detail: string;
  loop_discovered: number;
  image_url: string | null;
  is_key_clue: boolean;
}

export interface CharacterProfile {
  name: string;
  role: string;
  description: string;
  portrait_url: string | null;
  voice_style: string;
}

export interface LoopEntry {
  loop_number: number;
  summary: string;
  actions_taken: string[];
  clues_found: string[];
  duration_seconds: number;
  status: LoopStatus;
  death_description: string;
  scene_image_url: string | null;
  death_image_url: string | null;
}

export interface GameState {
  session_id: string;
  scenario: Scenario;
  current_loop: number;
  loop_status: LoopStatus;
  loop_start_time: number | null;
  loop_duration_seconds: number;
  clues: Clue[];
  loop_history: LoopEntry[];
  characters: CharacterProfile[];
  current_mood: Mood;
  total_clues_needed: number;
  can_break_loop: boolean;
  is_complete: boolean;
}

export interface AudioCue {
  track: string;
  volume: number;
  fade_in_ms: number;
  fade_out_ms: number;
}

export interface ScenarioInfo {
  id: Scenario;
  name: string;
  description: string;
  difficulty: string;
  estimated_loops: string;
}

export type WSMessageType =
  | "game_state"
  | "transcript_text"
  | "live_audio"
  | "live_turn_complete"
  | "scene_image"
  | "clue_discovered"
  | "clue_image"
  | "loop_failed"
  | "loop_broken"
  | "timer_update"
  | "mood_change"
  | "audio_cue"
  | "character_speaking"
  | "death_image"
  | "choices"
  | "can_break_loop"
  | "error";

export interface WSMessage {
  type: WSMessageType;
  data: unknown;
}
