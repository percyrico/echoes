import { useCallback, useEffect, useRef } from "react";
import { useGameStore } from "../store/gameStore";

const SAMPLE_RATE = 24000;
const PLAYBACK_RATE = 0.92; // slightly slower for clarity

export function useAudioPlayback() {
  const contextRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const scheduledCountRef = useRef(0);
  const checkDoneTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { pendingAudioChunks, clearAudioChunks, setNarratorSpeaking } =
    useGameStore();

  const getContext = useCallback(() => {
    if (!contextRef.current) {
      contextRef.current = new AudioContext({ sampleRate: SAMPLE_RATE });
    }
    return contextRef.current;
  }, []);

  // Schedule audio chunks gaplessly using precise timing
  const scheduleChunks = useCallback(
    (buffers: AudioBuffer[]) => {
      const ctx = getContext();

      // If we're behind current time, reset the schedule cursor
      if (nextStartTimeRef.current < ctx.currentTime) {
        nextStartTimeRef.current = ctx.currentTime + 0.02; // tiny lead-in
      }

      for (const buffer of buffers) {
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.playbackRate.value = PLAYBACK_RATE;
        source.connect(ctx.destination);
        source.start(nextStartTimeRef.current);

        // Advance cursor by the buffer's duration adjusted for playback rate
        nextStartTimeRef.current += buffer.duration / PLAYBACK_RATE;

        scheduledCountRef.current++;
        source.onended = () => {
          scheduledCountRef.current--;
        };
      }

      // Start a timer to detect when all scheduled audio has finished
      if (!checkDoneTimerRef.current) {
        checkDoneTimerRef.current = setInterval(() => {
          if (
            scheduledCountRef.current <= 0 &&
            useGameStore.getState().pendingAudioChunks.length === 0
          ) {
            setNarratorSpeaking(false);
            if (checkDoneTimerRef.current) {
              clearInterval(checkDoneTimerRef.current);
              checkDoneTimerRef.current = null;
            }
          }
        }, 200);
      }
    },
    [getContext, setNarratorSpeaking],
  );

  useEffect(() => {
    if (pendingAudioChunks.length === 0) return;

    const ctx = getContext();
    const buffers: AudioBuffer[] = [];

    for (const chunk of pendingAudioChunks) {
      const raw = atob(chunk);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) {
        bytes[i] = raw.charCodeAt(i);
      }

      const samples = new Int16Array(bytes.buffer);
      const audioBuffer = ctx.createBuffer(1, samples.length, SAMPLE_RATE);
      const channelData = audioBuffer.getChannelData(0);
      for (let i = 0; i < samples.length; i++) {
        channelData[i] = (samples[i] ?? 0) / 32768;
      }

      buffers.push(audioBuffer);
    }

    clearAudioChunks();
    scheduleChunks(buffers);
  }, [pendingAudioChunks, clearAudioChunks, getContext, scheduleChunks]);
}
