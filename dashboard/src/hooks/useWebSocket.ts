import { useCallback } from "react";
import { useGameStore } from "../store/gameStore";
import type {
  GameState,
  Clue,
  LoopEntry,
  AudioCue,
  Mood,
  CharacterProfile,
  WSMessage,
} from "../types";

// Module-level WebSocket — shared across ALL component instances
let sharedWs: WebSocket | null = null;
let onOpenCallback: (() => void) | null = null;

export function useWebSocket() {
  const connect = useCallback((onReady?: () => void) => {
    if (sharedWs) {
      sharedWs.close();
      sharedWs = null;
    }

    const state = useGameStore.getState();
    const sessionId = state.sessionId;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/ws/game/${sessionId}`);

    onOpenCallback = onReady ?? null;

    ws.onopen = () => {
      useGameStore.getState().setConnected(true);
      console.log("[WS] Connected");
      if (onOpenCallback) {
        onOpenCallback();
        onOpenCallback = null;
      }
    };

    ws.onclose = () => {
      useGameStore.getState().setConnected(false);
      console.log("[WS] Disconnected");
    };

    ws.onerror = (e) => {
      console.error("[WS] Error:", e);
    };

    ws.onmessage = (event: MessageEvent) => {
      const msg: WSMessage = JSON.parse(event.data as string);
      const s = useGameStore.getState();

      switch (msg.type) {
        case "game_state":
          s.setGameState(msg.data as GameState);
          break;
        case "transcript_text": {
          const txt = typeof msg.data === "string"
            ? msg.data
            : (msg.data as { text: string }).text;
          if (txt) s.addTranscriptLine(txt);
          break;
        }
        case "live_audio":
          s.setNarratorSpeaking(true);
          s.setChoices([]);  // clear choices while narrator speaks
          s.addAudioChunk(msg.data as string);
          break;
        case "live_turn_complete":
          s.setNarratorSpeaking(false);
          break;
        case "choices":
          s.setChoices((msg.data as { choices: string[] }).choices ?? []);
          break;
        case "scene_image": {
          const imgData = msg.data as { url?: string; image_url?: string };
          const imgUrl = imgData.url ?? imgData.image_url ?? null;
          console.log("[WS] Scene image received:", imgUrl);
          if (imgUrl) {
            // Add cache-buster so browser doesn't serve stale image
            s.setSceneImage(imgUrl + "?t=" + Date.now());
          }
          break;
        }
        case "clue_discovered": {
          const clue = msg.data as Clue;
          s.addClue(clue);
          s.triggerClueAnimation(clue);
          break;
        }
        case "clue_image": {
          const clueImg = msg.data as { clue_id: string; image_url: string };
          const store = useGameStore.getState();
          const updatedClues = store.clues.map((c) =>
            c.id === clueImg.clue_id
              ? { ...c, image_url: clueImg.image_url }
              : c,
          );
          useGameStore.setState({ clues: updatedClues });
          break;
        }
        case "loop_failed": {
          const failRaw = msg.data as Record<string, unknown>;
          const failEntry: LoopEntry = {
            loop_number: (failRaw.loop_number as number) ?? s.currentLoop,
            summary: (failRaw.summary as string) ?? "",
            actions_taken: (failRaw.actions_taken as string[]) ?? [],
            clues_found: (failRaw.clues_found as string[]) ?? [],
            duration_seconds: (failRaw.duration_seconds as number) ?? 0,
            status: "failed",
            death_description: (failRaw.death_description as string) ?? "The loop resets...",
            scene_image_url: null,
            death_image_url: null,
          };
          s.addLoopEntry(failEntry);
          s.setLastDeathDescription(failEntry.death_description);
          s.setView("loop_fail");
          break;
        }
        case "loop_broken": {
          const winRaw = msg.data as Record<string, unknown>;
          const winEntry: LoopEntry = {
            loop_number: (winRaw.loop_number as number) ?? s.currentLoop,
            summary: (winRaw.summary as string) ?? "The loop is broken!",
            actions_taken: [],
            clues_found: [],
            duration_seconds: (winRaw.duration_seconds as number) ?? 0,
            status: "broken",
            death_description: "",
            scene_image_url: null,
            death_image_url: null,
          };
          s.addLoopEntry(winEntry);
          s.setView("victory");
          break;
        }
        case "timer_update": {
          const timerData = msg.data as { seconds?: number; remaining_seconds?: number };
          s.setTimer(timerData.seconds ?? timerData.remaining_seconds ?? 0);
          break;
        }
        case "mood_change":
          s.setMood(
            (msg.data as { mood: Mood }).mood,
          );
          break;
        case "audio_cue":
          s.setAudioCue(msg.data as AudioCue);
          break;
        case "can_break_loop":
          s.setCanBreakLoop(true);
          break;
        case "character_speaking":
          s.setSpeakingCharacter(msg.data as CharacterProfile | null);
          break;
        case "death_image": {
          const deathData = msg.data as { url?: string; image_url?: string };
          s.setDeathImage(deathData.url ?? deathData.image_url ?? null);
          break;
        }
        case "error":
          console.error("Server error:", msg.data);
          break;
      }
    };

    sharedWs = ws;
  }, []);

  const disconnect = useCallback(() => {
    if (sharedWs) {
      sharedWs.close();
      sharedWs = null;
    }
  }, []);

  const sendJSON = useCallback((data: Record<string, unknown>) => {
    if (sharedWs?.readyState === WebSocket.OPEN) {
      console.log("[WS] Sending:", data.type);
      sharedWs.send(JSON.stringify(data));
    } else {
      console.warn("[WS] Cannot send — WebSocket not open. State:", sharedWs?.readyState);
    }
  }, []);

  const sendBinary = useCallback((data: ArrayBuffer) => {
    if (sharedWs?.readyState === WebSocket.OPEN) {
      sharedWs.send(data);
    }
  }, []);

  return { connect, disconnect, sendJSON, sendBinary };
}
