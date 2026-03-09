import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "../store/gameStore";

type Tab = "clues" | "loops";

export default function CluePanel() {
  const [tab, setTab] = useState<Tab>("clues");
  const clues = useGameStore((s) => s.clues);
  const loopHistory = useGameStore((s) => s.loopHistory);
  const currentLoop = useGameStore((s) => s.currentLoop);
  const totalCluesNeeded = useGameStore((s) => s.totalCluesNeeded);
  const newClueAnimation = useGameStore((s) => s.newClueAnimation);

  const keyClues = clues.filter((c) => c.is_key_clue);
  const progress = clues.length;

  return (
    <div className="flex flex-col h-full bg-echo-surface/60 border border-echo-border rounded-xl overflow-hidden">
      {/* Tab toggle */}
      <div className="flex border-b border-echo-border">
        <button
          onClick={() => setTab("clues")}
          className={`flex-1 py-2.5 text-xs font-display font-semibold transition-colors ${
            tab === "clues"
              ? "text-echo-clue bg-echo-clue/10 border-b-2 border-echo-clue"
              : "text-echo-muted hover:text-echo-text"
          }`}
        >
          Clues ({progress})
        </button>
        <button
          onClick={() => setTab("loops")}
          className={`flex-1 py-2.5 text-xs font-display font-semibold transition-colors ${
            tab === "loops"
              ? "text-echo-accent bg-echo-accent/10 border-b-2 border-echo-accent"
              : "text-echo-muted hover:text-echo-text"
          }`}
        >
          Loops ({loopHistory.length})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        <AnimatePresence mode="wait">
          {tab === "clues" ? (
            <motion.div
              key="clues"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              className="space-y-2"
            >
              {/* Progress bar */}
              <div className="mb-3">
                <div className="flex justify-between text-[10px] text-echo-muted mb-1 font-mono">
                  <span>{progress}/{totalCluesNeeded} clues found</span>
                  <span>{keyClues.length} key</span>
                </div>
                <div className="h-1.5 bg-echo-bg rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-echo-clue/60 to-echo-clue"
                    animate={{ width: `${(progress / Math.max(1, totalCluesNeeded)) * 100}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
              </div>

              {/* Clue list */}
              {clues.map((clue) => (
                <motion.div
                  key={clue.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`p-2.5 rounded-lg border transition-all ${
                    clue.is_key_clue
                      ? "border-echo-clue/40 bg-echo-clue/5"
                      : "border-echo-border/50 bg-echo-panel/50"
                  } ${
                    newClueAnimation?.id === clue.id ? "glow-clue" : ""
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {clue.image_url ? (
                      <img
                        src={clue.image_url}
                        alt=""
                        className="w-10 h-10 rounded object-cover flex-shrink-0 border border-echo-border/30"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded bg-echo-bg/50 flex items-center justify-center flex-shrink-0 border border-echo-border/30">
                        <span className="text-echo-clue text-sm">
                          {clue.is_key_clue ? "\u2B50" : "\u2727"}
                        </span>
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-echo-text text-xs font-display leading-tight">
                        {clue.text}
                      </p>
                      <p className="text-echo-muted text-[10px] mt-1 font-mono">
                        Loop {clue.loop_discovered}
                        {clue.is_key_clue && (
                          <span className="text-echo-clue ml-1">KEY</span>
                        )}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}

              {/* Locked clue placeholders */}
              {Array.from({ length: Math.max(0, totalCluesNeeded - progress) }).map((_, i) => (
                <div
                  key={`locked-${i}`}
                  className="p-2.5 rounded-lg border border-echo-border/20 bg-echo-bg/30"
                >
                  <div className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded bg-echo-bg/50 flex items-center justify-center flex-shrink-0">
                      <span className="text-echo-muted/30 text-sm">{"\u{1F512}"}</span>
                    </div>
                    <span className="text-echo-muted/30 text-xs font-mono">???</span>
                  </div>
                </div>
              ))}
            </motion.div>
          ) : (
            <motion.div
              key="loops"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="space-y-2"
            >
              {/* Current loop */}
              <div className="p-2.5 rounded-lg border border-echo-accent/30 bg-echo-accent/5">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-echo-accent text-xs font-display font-semibold">
                    Loop {currentLoop}
                  </span>
                  <span className="text-echo-accent text-[10px] font-mono">ACTIVE</span>
                </div>
                <p className="text-echo-muted text-[10px]">In progress...</p>
              </div>

              {/* Past loops (reverse chronological) */}
              {[...loopHistory].reverse().map((entry) => (
                <div
                  key={entry.loop_number}
                  className="p-2.5 rounded-lg border border-echo-border/30 bg-echo-panel/30"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-echo-text text-xs font-display font-semibold">
                      Loop {entry.loop_number}
                    </span>
                    <span className="text-xs">
                      {entry.status === "broken" ? (
                        <span className="text-echo-success">{"\u2713"}</span>
                      ) : (
                        <span className="text-echo-danger">{"\u2620"}</span>
                      )}
                    </span>
                  </div>
                  <p className="text-echo-muted text-[10px] leading-relaxed line-clamp-2">
                    {entry.summary}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-echo-muted/60 text-[9px] font-mono">
                      {Math.floor(entry.duration_seconds / 60)}m {entry.duration_seconds % 60}s
                    </span>
                    {entry.clues_found.length > 0 && (
                      <span className="text-echo-clue text-[9px] font-mono">
                        +{entry.clues_found.length} clue{entry.clues_found.length !== 1 ? "s" : ""}
                      </span>
                    )}
                  </div>
                </div>
              ))}

              {loopHistory.length === 0 && (
                <div className="text-center py-6 text-echo-muted/40 text-xs">
                  First loop. No history yet.
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
