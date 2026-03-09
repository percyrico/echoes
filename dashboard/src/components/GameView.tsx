import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "../store/gameStore";
import { useWebSocket } from "../hooks/useWebSocket";
import { useAudioPlayback } from "../hooks/useAudioPlayback";
import SceneImage from "./SceneImage";
import NarratorBox from "./NarratorBox";
import CluePanel from "./CluePanel";
import LoopTimer from "./LoopTimer";
import AudioEngine from "./AudioEngine";
import MoodParticles from "./MoodParticles";
import ClueDiscoveryOverlay from "./ClueDiscoveryOverlay";
import GlitchEffect from "./GlitchEffect";

const SCENARIO_NAMES: Record<string, string> = {
  last_train: "The Last Train",
  locked_room: "The Locked Room",
  dinner_party: "The Dinner Party",
  the_signal: "The Signal",
  the_crash: "The Crash",
  the_heist: "The Heist",
  room_414: "Room 414",
  the_factory: "The Factory",
};

const MOOD_LABELS: Record<string, string> = {
  tense: "Tense",
  calm: "Calm",
  urgent: "URGENT",
  mysterious: "Mysterious",
  dread: "Dread",
  revelation: "Revelation",
};

export default function GameView() {
  const scenario = useGameStore((s) => s.scenario);
  const currentLoop = useGameStore((s) => s.currentLoop);
  const currentMood = useGameStore((s) => s.currentMood);
  const timerSeconds = useGameStore((s) => s.timerSeconds);
  const canBreakLoop = useGameStore((s) => s.canBreakLoop);
  const choices = useGameStore((s) => s.choices);
  const isNarratorSpeaking = useGameStore((s) => s.isNarratorSpeaking);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { sendJSON } = useWebSocket();
  useAudioPlayback();

  const handleChoice = useCallback((choice: string) => {
    sendJSON({ type: "user_text", text: choice });
    useGameStore.getState().setChoices([]);
    useGameStore.getState().setWaitingForChoice(false);
  }, [sendJSON]);

  const handleBreakLoop = useCallback(() => {
    sendJSON({ type: "break_loop" });
  }, [sendJSON]);

  const isDanger = timerSeconds <= 60;
  const isCritical = timerSeconds <= 30;

  const moodLabel = MOOD_LABELS[currentMood] ?? currentMood;

  return (
    <div className="relative h-full w-full flex flex-col overflow-hidden">
      {/* Background particles */}
      <MoodParticles mood={currentMood} />

      {/* Glitch on critical timer */}
      <GlitchEffect active={isCritical} intensity="low" />

      {/* Critical border pulse */}
      <AnimatePresence>
        {isDanger && (
          <motion.div
            className="absolute inset-0 pointer-events-none z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="absolute inset-0 border-2 rounded-none"
              style={{ borderColor: isCritical ? "#ff4757" : "#f5a623" }}
              animate={{ opacity: [0.3, 0.8, 0.3] }}
              transition={{ duration: isCritical ? 0.5 : 1, repeat: Infinity }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <header className="relative z-20 flex items-center justify-between px-4 py-3 border-b border-echo-border/50 bg-echo-bg/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <h2 className="text-echo-text font-display font-semibold text-sm">
            {scenario ? SCENARIO_NAMES[scenario] ?? scenario : ""}
          </h2>
          <span className="text-echo-accent text-xs font-mono bg-echo-accent/10 px-2 py-0.5 rounded">
            Loop {currentLoop}
          </span>
        </div>

        <div className="flex items-center gap-4">
          {/* Mood indicator */}
          <span
            className={`text-xs font-display px-2 py-0.5 rounded ${
              currentMood === "urgent" || currentMood === "dread"
                ? "text-echo-danger bg-echo-danger/10"
                : currentMood === "revelation"
                  ? "text-echo-clue bg-echo-clue/10"
                  : "text-echo-muted bg-echo-surface"
            }`}
          >
            {moodLabel}
          </span>

          {/* Timer */}
          <LoopTimer />

          {/* Sidebar toggle (mobile) */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="md:hidden text-echo-muted hover:text-echo-text p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="relative z-10 flex-1 flex overflow-hidden">
        {/* Center column */}
        <div className="flex-1 flex flex-col overflow-hidden p-3 md:p-4 gap-2 md:gap-3">
          {/* Scrollable content: image + narrator */}
          <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-2 md:gap-3">
            {/* Scene image */}
            <SceneImage />

            {/* Narrator box */}
            <div className="flex-1 min-h-[120px]">
              <NarratorBox />
            </div>
          </div>

          {/* Fixed bottom: break loop + choices — always visible */}
          <div className="shrink-0">
            {/* Break loop button */}
            <AnimatePresence>
              {canBreakLoop && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className="flex justify-center mb-2"
                >
                  <motion.button
                    onClick={handleBreakLoop}
                    className="px-6 py-2 rounded-xl bg-echo-success/20 border border-echo-success/50 text-echo-success font-display font-semibold text-sm hover:bg-echo-success/30 transition-all"
                    animate={{ boxShadow: ["0 0 10px rgba(46,213,115,0.2)", "0 0 25px rgba(46,213,115,0.4)", "0 0 10px rgba(46,213,115,0.2)"] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    Break the Loop
                  </motion.button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Choice buttons */}
            <AnimatePresence mode="wait">
              {choices.length > 0 ? (
                <motion.div
                  key="choices"
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.4 }}
                  className="flex flex-col gap-2"
                >
                  <p className="text-echo-muted text-xs font-display text-center">
                    What do you do?
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 md:gap-2 max-h-[40vh] overflow-y-auto">
                    {choices.map((choice, i) => (
                      <motion.button
                        key={choice}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.08, duration: 0.3 }}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => handleChoice(choice)}
                        className="text-left px-3 py-2 md:px-4 md:py-3 rounded-xl border border-echo-border/60 bg-echo-surface/60 hover:border-echo-accent/50 hover:bg-echo-accent/10 text-echo-text text-xs md:text-sm font-story transition-all"
                      >
                        <span className="text-echo-accent font-display font-semibold mr-1.5 text-xs">
                          {String.fromCharCode(65 + i)}.
                        </span>
                        {choice}
                      </motion.button>
                    ))}
                  </div>
                </motion.div>
              ) : isNarratorSpeaking ? (
                <motion.div
                  key="speaking"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center justify-center gap-2 py-2"
                >
                  <div className="flex items-center gap-1">
                    {[0, 1, 2, 3, 4].map((i) => (
                      <motion.div
                        key={i}
                        className="w-1 bg-echo-accent rounded-full"
                        animate={{ height: [4, 14, 4] }}
                        transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.1 }}
                      />
                    ))}
                  </div>
                  <span className="text-echo-muted text-xs font-display">Narrator is speaking...</span>
                </motion.div>
              ) : (
                <motion.div
                  key="waiting"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.5 }}
                  className="text-center py-2"
                >
                  <span className="text-echo-muted/50 text-xs font-display">Listening...</span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Sidebar */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 280, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="hidden md:block overflow-hidden border-l border-echo-border/50"
            >
              <div className="w-[280px] h-full p-3">
                <CluePanel />
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Mobile sidebar overlay */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25 }}
              className="md:hidden absolute right-0 top-0 bottom-0 w-72 bg-echo-bg border-l border-echo-border z-30 p-3"
            >
              <button
                onClick={() => setSidebarOpen(false)}
                className="absolute top-2 right-2 text-echo-muted hover:text-echo-text"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              <CluePanel />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Overlays */}
      <ClueDiscoveryOverlay />
      <AudioEngine />
    </div>
  );
}
