import { create } from "zustand";
import type {
  Scenario,
  LoopStatus,
  Mood,
  Clue,
  LoopEntry,
  CharacterProfile,
  AudioCue,
  GameState,
} from "../types";

type AppView = "lobby" | "game" | "loop_fail" | "victory";

interface GameStoreState {
  // App state
  view: AppView;
  sessionId: string;
  scenario: Scenario | null;
  connected: boolean;
  playerName: string;

  // Game state
  gameState: GameState | null;
  currentLoop: number;
  loopStatus: LoopStatus;
  clues: Clue[];
  loopHistory: LoopEntry[];
  characters: CharacterProfile[];
  currentMood: Mood;
  timerSeconds: number;
  canBreakLoop: boolean;
  totalCluesNeeded: number;

  // UI state
  isRecording: boolean;
  isNarratorSpeaking: boolean;
  pendingAudioChunks: string[];
  transcriptLines: string[];
  choices: string[];
  waitingForChoice: boolean;
  sceneImageUrl: string | null;
  currentAudioCue: AudioCue | null;
  newClueAnimation: Clue | null;
  deathImageUrl: string | null;
  speakingCharacter: CharacterProfile | null;
  lastDeathDescription: string;

  // Actions
  setView: (view: AppView) => void;
  setScenario: (scenario: Scenario) => void;
  setPlayerName: (name: string) => void;
  setConnected: (connected: boolean) => void;
  setGameState: (state: GameState) => void;
  addClue: (clue: Clue) => void;
  addLoopEntry: (entry: LoopEntry) => void;
  setTimer: (seconds: number) => void;
  setMood: (mood: Mood) => void;
  setRecording: (recording: boolean) => void;
  setNarratorSpeaking: (speaking: boolean) => void;
  addAudioChunk: (chunk: string) => void;
  clearAudioChunks: () => void;
  addTranscriptLine: (line: string) => void;
  clearTranscript: () => void;
  setSceneImage: (url: string | null) => void;
  setAudioCue: (cue: AudioCue) => void;
  setCanBreakLoop: (can: boolean) => void;
  setChoices: (choices: string[]) => void;
  setWaitingForChoice: (waiting: boolean) => void;
  triggerClueAnimation: (clue: Clue) => void;
  clearClueAnimation: () => void;
  setDeathImage: (url: string | null) => void;
  setSpeakingCharacter: (character: CharacterProfile | null) => void;
  setLastDeathDescription: (desc: string) => void;
  resetForNewLoop: () => void;
  resetGame: () => void;
}

export const useGameStore = create<GameStoreState>((set) => ({
  view: "lobby",
  sessionId: crypto.randomUUID().slice(0, 8),
  scenario: null,
  connected: false,
  playerName: "",

  gameState: null,
  currentLoop: 1,
  loopStatus: "active",
  clues: [],
  loopHistory: [],
  characters: [],
  currentMood: "mysterious",
  timerSeconds: 300,
  canBreakLoop: false,
  totalCluesNeeded: 8,

  isRecording: false,
  isNarratorSpeaking: false,
  pendingAudioChunks: [],
  transcriptLines: [],
  choices: [],
  waitingForChoice: false,
  sceneImageUrl: null,
  currentAudioCue: null,
  newClueAnimation: null,
  deathImageUrl: null,
  speakingCharacter: null,
  lastDeathDescription: "",

  setView: (view) => set({ view }),
  setScenario: (scenario) => set({ scenario }),
  setPlayerName: (name) => set({ playerName: name }),
  setConnected: (connected) => set({ connected }),

  setGameState: (state) =>
    set({
      gameState: state,
      currentLoop: state.current_loop,
      loopStatus: state.loop_status,
      clues: state.clues,
      loopHistory: state.loop_history,
      characters: state.characters,
      currentMood: state.current_mood,
      timerSeconds: state.loop_duration_seconds,
      canBreakLoop: state.can_break_loop,
      totalCluesNeeded: state.total_clues_needed,
    }),

  addClue: (clue) =>
    set((s) => ({
      clues: s.clues.some((c) => c.id === clue.id)
        ? s.clues
        : [...s.clues, clue],
    })),

  addLoopEntry: (entry) =>
    set((s) => ({ loopHistory: [...s.loopHistory, entry] })),

  setTimer: (seconds) => set({ timerSeconds: seconds }),
  setMood: (mood) => set({ currentMood: mood }),
  setRecording: (recording) => set({ isRecording: recording }),
  setNarratorSpeaking: (speaking) => set({ isNarratorSpeaking: speaking }),

  addAudioChunk: (chunk) =>
    set((s) => ({ pendingAudioChunks: [...s.pendingAudioChunks, chunk] })),
  clearAudioChunks: () => set({ pendingAudioChunks: [] }),

  addTranscriptLine: (line) =>
    set((s) => {
      const lines = [...s.transcriptLines];
      if (lines.length === 0) {
        // First fragment — start a new paragraph
        lines.push(line);
      } else {
        // Append to the last paragraph
        const last = lines[lines.length - 1];
        const merged = last + line;
        lines[lines.length - 1] = merged;

        // If the merged text ends with sentence punctuation followed by space/end,
        // start a new paragraph for the next fragment
        if (/[.!?]["']?\s*$/.test(merged) && merged.length > 80) {
          lines.push("");
        }
      }
      // Remove trailing empty string if it's the only content
      const filtered = lines.filter((l, i) => i < lines.length - 1 || l !== "");
      return { transcriptLines: filtered };
    }),
  clearTranscript: () => set({ transcriptLines: [] }),

  setSceneImage: (url) => set({ sceneImageUrl: url }),
  setAudioCue: (cue) => set({ currentAudioCue: cue }),
  setCanBreakLoop: (can) => set({ canBreakLoop: can }),
  setChoices: (choices) => set({ choices, waitingForChoice: choices.length > 0 }),
  setWaitingForChoice: (waiting) => set({ waitingForChoice: waiting }),

  triggerClueAnimation: (clue) => set({ newClueAnimation: clue }),
  clearClueAnimation: () => set({ newClueAnimation: null }),

  setDeathImage: (url) => set({ deathImageUrl: url }),
  setSpeakingCharacter: (character) => set({ speakingCharacter: character }),
  setLastDeathDescription: (desc) => set({ lastDeathDescription: desc }),

  resetForNewLoop: () =>
    set((s) => ({
      view: "game",
      loopStatus: "active",
      transcriptLines: [],
      choices: [],
      waitingForChoice: false,
      sceneImageUrl: null,
      deathImageUrl: null,
      currentLoop: s.currentLoop + 1,
      isRecording: false,
      isNarratorSpeaking: false,
      speakingCharacter: null,
    })),

  resetGame: () =>
    set({
      view: "lobby",
      sessionId: crypto.randomUUID().slice(0, 8),
      scenario: null,
      connected: false,
      playerName: "",
      gameState: null,
      currentLoop: 1,
      loopStatus: "active",
      clues: [],
      loopHistory: [],
      characters: [],
      currentMood: "mysterious",
      timerSeconds: 300,
      canBreakLoop: false,
      totalCluesNeeded: 8,
      isRecording: false,
      isNarratorSpeaking: false,
      pendingAudioChunks: [],
      transcriptLines: [],
      sceneImageUrl: null,
      currentAudioCue: null,
      newClueAnimation: null,
      deathImageUrl: null,
      speakingCharacter: null,
      lastDeathDescription: "",
    }),
}));
