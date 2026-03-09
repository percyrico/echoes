import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "../store/gameStore";

export default function NarratorBox() {
  const transcriptLines = useGameStore((s) => s.transcriptLines);
  const isNarratorSpeaking = useGameStore((s) => s.isNarratorSpeaking);
  const speakingCharacter = useGameStore((s) => s.speakingCharacter);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcriptLines]);

  return (
    <div className="relative flex flex-col rounded-xl bg-echo-surface/80 border border-echo-border overflow-hidden">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-echo-accent/[0.03] to-transparent pointer-events-none" />

      {/* Transcript area */}
      <div
        ref={scrollRef}
        className="relative flex-1 overflow-y-auto p-4 space-y-3 min-h-[160px] max-h-[280px]"
      >
        <AnimatePresence initial={false}>
          {transcriptLines.filter(Boolean).map((line, i) => (
            <motion.div
              key={`${i}-${String(line).slice(0, 20)}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="text-echo-text/90 font-story text-base leading-relaxed"
            >
              {line}
            </motion.div>
          ))}
        </AnimatePresence>

        {transcriptLines.length === 0 && (
          <div className="text-echo-muted/50 font-story text-base italic text-center py-8">
            The narrator awaits your voice...
          </div>
        )}
      </div>

      {/* Speaking indicator bar */}
      <AnimatePresence>
        {isNarratorSpeaking && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-echo-border/50 px-4 py-2 flex items-center gap-3"
          >
            {/* Character portrait */}
            {speakingCharacter?.portrait_url && (
              <img
                src={speakingCharacter.portrait_url}
                alt={speakingCharacter.name}
                className="w-8 h-8 rounded-full border border-echo-accent/40 object-cover"
              />
            )}

            {/* Character name */}
            {speakingCharacter && (
              <span className="text-echo-accent text-xs font-display font-semibold">
                {speakingCharacter.name}
              </span>
            )}

            {/* Waveform animation */}
            <div className="flex items-center gap-0.5 ml-auto">
              {Array.from({ length: 5 }).map((_, i) => (
                <motion.div
                  key={i}
                  className="w-0.5 bg-echo-accent rounded-full"
                  animate={{
                    height: [4, 12 + Math.random() * 8, 4],
                  }}
                  transition={{
                    duration: 0.5 + Math.random() * 0.3,
                    repeat: Infinity,
                    delay: i * 0.1,
                  }}
                />
              ))}
              <span className="text-echo-muted text-xs ml-2 font-display">
                Speaking...
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
