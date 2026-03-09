import { motion } from "framer-motion";
import { useGameStore } from "../store/gameStore";
import { useWebSocket } from "../hooks/useWebSocket";
import GlitchEffect from "./GlitchEffect";

export default function LoopFailScreen() {
  const currentLoop = useGameStore((s) => s.currentLoop);
  const lastDeathDescription = useGameStore((s) => s.lastDeathDescription);
  const deathImageUrl = useGameStore((s) => s.deathImageUrl);
  const loopHistory = useGameStore((s) => s.loopHistory);
  const newClueAnimation = useGameStore((s) => s.newClueAnimation);
  const clues = useGameStore((s) => s.clues);
  const resetForNewLoop = useGameStore((s) => s.resetForNewLoop);
  const { sendJSON } = useWebSocket();

  const lastLoop = loopHistory[loopHistory.length - 1];
  const survivalTime = lastLoop
    ? `${Math.floor(lastLoop.duration_seconds / 60)}m ${lastLoop.duration_seconds % 60}s`
    : "--";

  const latestClue = clues.length > 0 ? clues[clues.length - 1] : null;
  const hasNewClue = lastLoop && lastLoop.clues_found.length > 0;

  const handleNextLoop = () => {
    resetForNewLoop();
    sendJSON({ type: "restart_loop" });
  };

  return (
    <motion.div
      className="relative h-full w-full flex items-center justify-center overflow-hidden bg-echo-bg"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Glitch overlay */}
      <GlitchEffect active={true} intensity="high" />

      {/* Expanding rings (time rewind) */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {[0, 1, 2, 3].map((i) => (
          <motion.div
            key={i}
            className="absolute border border-echo-accent/20 rounded-full"
            style={{ width: 100, height: 100 }}
            animate={{
              scale: [1, 4 + i],
              opacity: [0.4, 0],
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              delay: i * 0.7,
              ease: "easeOut",
            }}
          />
        ))}
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center gap-6 px-6 max-w-lg w-full text-center">
        {/* Failed text with glitch */}
        <motion.div
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", damping: 15, delay: 0.3 }}
        >
          <h1 className="text-echo-danger text-4xl md:text-5xl font-display font-bold glitch-text">
            LOOP {currentLoop} FAILED
          </h1>
        </motion.div>

        {/* Death image */}
        {deathImageUrl && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.6, duration: 0.6 }}
            className="w-full max-w-sm rounded-xl overflow-hidden border border-echo-danger/30"
          >
            <img
              src={deathImageUrl}
              alt="Death scene"
              className="w-full h-48 object-cover"
              style={{ filter: "saturate(0.7) contrast(1.1)" }}
            />
          </motion.div>
        )}

        {/* Death description */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.5 }}
          className="text-echo-text/80 font-story text-lg italic leading-relaxed max-w-md"
        >
          {lastDeathDescription || "The loop resets. Time folds back on itself."}
        </motion.p>

        {/* Survival time */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="text-echo-muted text-sm font-mono"
        >
          Survived: {survivalTime}
        </motion.div>

        {/* New clue card */}
        {hasNewClue && latestClue && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2, type: "spring", damping: 20 }}
            className={`w-full max-w-sm p-4 rounded-xl border bg-echo-panel ${
              newClueAnimation ? "border-echo-clue/50 glow-clue" : "border-echo-clue/30"
            }`}
          >
            <p className="text-echo-clue text-xs font-display font-bold uppercase tracking-wider mb-2">
              New Clue Discovered
            </p>
            <div className="flex items-start gap-3">
              {latestClue.image_url ? (
                <img
                  src={latestClue.image_url}
                  alt=""
                  className="w-12 h-12 rounded-lg object-cover border border-echo-clue/20"
                />
              ) : (
                <div className="w-12 h-12 rounded-lg bg-echo-clue/10 flex items-center justify-center">
                  <span className="text-lg">{latestClue.is_key_clue ? "\u2B50" : "\u2727"}</span>
                </div>
              )}
              <div className="text-left flex-1">
                <p className="text-echo-text text-sm font-story">{latestClue.text}</p>
                {latestClue.is_key_clue && (
                  <span className="text-echo-clue text-[10px] font-mono mt-1 inline-block">KEY CLUE</span>
                )}
              </div>
            </div>
          </motion.div>
        )}

        {/* Next loop button */}
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          onClick={handleNextLoop}
          className="px-8 py-3 rounded-xl bg-echo-accent text-white font-display font-semibold text-base hover:bg-echo-accent/90 glow-accent transition-all"
        >
          Begin Loop {currentLoop + 1} {"\u2192"}
        </motion.button>
      </div>
    </motion.div>
  );
}
