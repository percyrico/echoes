import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "../store/gameStore";

export default function ClueDiscoveryOverlay() {
  const newClue = useGameStore((s) => s.newClueAnimation);
  const clearClueAnimation = useGameStore((s) => s.clearClueAnimation);

  useEffect(() => {
    if (newClue) {
      const timer = setTimeout(() => {
        clearClueAnimation();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [newClue, clearClueAnimation]);

  return (
    <AnimatePresence>
      {newClue && (
        <motion.div
          initial={{ opacity: 0, y: 80 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -30 }}
          transition={{ type: "spring", damping: 20, stiffness: 300 }}
          className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50"
        >
          <div className="relative glow-clue rounded-xl overflow-hidden">
            {/* Background */}
            <div className="bg-echo-panel border border-echo-clue/40 rounded-xl p-4 pr-6 flex items-center gap-4 min-w-[300px]">
              {/* Icon / Thumbnail */}
              {newClue.image_url ? (
                <img
                  src={newClue.image_url}
                  alt=""
                  className="w-14 h-14 rounded-lg object-cover border border-echo-clue/30"
                />
              ) : (
                <div className="w-14 h-14 rounded-lg bg-echo-clue/10 flex items-center justify-center border border-echo-clue/30">
                  <motion.span
                    className="text-2xl"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 0.6, repeat: 2 }}
                  >
                    {newClue.is_key_clue ? "\u2B50" : "\u2727"}
                  </motion.span>
                </div>
              )}

              <div>
                <motion.p
                  className="text-echo-clue text-xs font-display font-bold uppercase tracking-wider"
                  animate={{ opacity: [0.6, 1, 0.6] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                >
                  {newClue.is_key_clue ? "Key Clue Discovered" : "Clue Discovered"}
                </motion.p>
                <p className="text-echo-text text-sm font-story mt-1 max-w-[240px]">
                  {newClue.text}
                </p>
              </div>
            </div>

            {/* Shine animation */}
            <motion.div
              className="absolute inset-0 pointer-events-none rounded-xl"
              animate={{
                background: [
                  "linear-gradient(90deg, transparent 0%, rgba(245,166,35,0.15) 50%, transparent 100%)",
                  "linear-gradient(90deg, transparent 100%, rgba(245,166,35,0.15) 150%, transparent 200%)",
                ],
              }}
              transition={{ duration: 1.5, repeat: 1 }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
