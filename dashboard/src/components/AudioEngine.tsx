import { useEffect, useRef } from "react";
import { useGameStore } from "../store/gameStore";

export default function AudioEngine() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentAudioCue = useGameStore((s) => s.currentAudioCue);
  const isNarratorSpeaking = useGameStore((s) => s.isNarratorSpeaking);
  const currentTrackRef = useRef<string | null>(null);
  const targetVolumeRef = useRef(0.1);
  const fadeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Duck volume when narrator is speaking
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const duckTo = isNarratorSpeaking
      ? targetVolumeRef.current * 0.25
      : targetVolumeRef.current;

    const step = () => {
      const diff = duckTo - audio.volume;
      if (Math.abs(diff) < 0.005) {
        audio.volume = duckTo;
        return;
      }
      audio.volume += diff * 0.15;
      fadeTimerRef.current = setTimeout(step, 50);
    };
    step();

    return () => {
      if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current);
    };
  }, [isNarratorSpeaking]);

  // Track changes
  useEffect(() => {
    if (!currentAudioCue) return;
    if (currentAudioCue.track === currentTrackRef.current) return;

    currentTrackRef.current = currentAudioCue.track;
    targetVolumeRef.current = currentAudioCue.volume;

    const audio = audioRef.current;
    if (!audio) return;

    const fadeOut = () => {
      if (audio.volume > 0.01) {
        audio.volume = Math.max(0, audio.volume - 0.01);
        setTimeout(fadeOut, currentAudioCue.fade_out_ms / 40);
      } else {
        audio.pause();
        audio.src = `/assets/audio/${currentAudioCue.track}.wav`;
        audio.volume = 0;
        audio.loop = true;
        audio.play().catch(() => {});
        fadeIn();
      }
    };

    const fadeIn = () => {
      const target = isNarratorSpeaking
        ? currentAudioCue.volume * 0.25
        : currentAudioCue.volume;
      if (audio.volume < target - 0.005) {
        audio.volume = Math.min(target, audio.volume + 0.005);
        setTimeout(fadeIn, currentAudioCue.fade_in_ms / 40);
      }
    };

    if (audio.src && !audio.paused) {
      fadeOut();
    } else {
      audio.src = `/assets/audio/${currentAudioCue.track}.wav`;
      audio.volume = 0;
      audio.loop = true;
      audio.play().catch(() => {});
      fadeIn();
    }
  }, [currentAudioCue, isNarratorSpeaking]);

  return <audio ref={audioRef} className="hidden" />;
}
