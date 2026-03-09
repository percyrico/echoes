import { motion } from "framer-motion";
import { useGameStore } from "../store/gameStore";
import { exportStoryPDF } from "./StoryExport";

export default function VictoryScreen() {
  const currentLoop = useGameStore((s) => s.currentLoop);
  const clues = useGameStore((s) => s.clues);
  const loopHistory = useGameStore((s) => s.loopHistory);
  const totalCluesNeeded = useGameStore((s) => s.totalCluesNeeded);
  const resetGame = useGameStore((s) => s.resetGame);
  const scenario = useGameStore((s) => s.scenario);

  const totalTime = loopHistory.reduce((sum, l) => sum + l.duration_seconds, 0);
  const totalMinutes = Math.floor(totalTime / 60);
  const totalSecs = totalTime % 60;

  const victoryEntry = loopHistory[loopHistory.length - 1];
  const victoryText = victoryEntry?.summary ?? "You broke free from the loop.";

  const handleNewScenario = () => {
    resetGame();
  };

  const handlePlayAgain = () => {
    const s = scenario;
    resetGame();
    if (s) {
      useGameStore.getState().setScenario(s);
    }
  };

  return (
    <motion.div
      className="relative h-full w-full flex items-center justify-center overflow-hidden bg-echo-bg"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.8 }}
    >
      {/* Background celebration particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {Array.from({ length: 30 }).map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              backgroundColor:
                i % 3 === 0
                  ? "#7c6ff5"
                  : i % 3 === 1
                    ? "#f5a623"
                    : "#2ed573",
            }}
            animate={{
              y: [0, -200 - Math.random() * 300],
              opacity: [0.8, 0],
              scale: [1, 0],
            }}
            transition={{
              duration: 2 + Math.random() * 2,
              repeat: Infinity,
              delay: Math.random() * 3,
            }}
          />
        ))}
      </div>

      {/* Shatter / break rings */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {[0, 1, 2, 3, 4].map((i) => (
          <motion.div
            key={i}
            className="absolute border border-echo-success/30 rounded-full"
            style={{ width: 80, height: 80 }}
            initial={{ scale: 0, opacity: 0.8 }}
            animate={{ scale: 3 + i * 1.5, opacity: 0 }}
            transition={{
              duration: 2,
              delay: 0.3 + i * 0.3,
              ease: "easeOut",
            }}
          />
        ))}
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center gap-6 px-6 max-w-lg w-full text-center">
        {/* Victory text */}
        <motion.div
          initial={{ scale: 0.3, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", damping: 12, delay: 0.5 }}
        >
          <h1 className="text-echo-success text-5xl md:text-6xl font-display font-bold">
            LOOP BROKEN
          </h1>
        </motion.div>

        {/* Victory narration */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1, duration: 0.6 }}
          className="text-echo-text/90 font-story text-lg italic leading-relaxed max-w-md"
        >
          {victoryText}
        </motion.p>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.3 }}
          className="grid grid-cols-3 gap-4 w-full max-w-sm"
        >
          <div className="bg-echo-surface border border-echo-border rounded-xl p-3">
            <p className="text-echo-accent text-2xl font-display font-bold">{currentLoop}</p>
            <p className="text-echo-muted text-[10px] font-mono mt-1">LOOPS</p>
          </div>
          <div className="bg-echo-surface border border-echo-border rounded-xl p-3">
            <p className="text-echo-clue text-2xl font-display font-bold">
              {clues.length}/{totalCluesNeeded}
            </p>
            <p className="text-echo-muted text-[10px] font-mono mt-1">CLUES</p>
          </div>
          <div className="bg-echo-surface border border-echo-border rounded-xl p-3">
            <p className="text-echo-text text-2xl font-display font-bold">
              {totalMinutes}:{totalSecs.toString().padStart(2, "0")}
            </p>
            <p className="text-echo-muted text-[10px] font-mono mt-1">TOTAL TIME</p>
          </div>
        </motion.div>

        {/* Loop history summary */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.6 }}
          className="w-full max-w-sm max-h-40 overflow-y-auto"
        >
          <div className="space-y-1.5">
            {loopHistory.map((entry) => (
              <div
                key={entry.loop_number}
                className="flex items-center gap-2 text-xs px-3 py-1.5 bg-echo-panel/40 rounded-lg"
              >
                <span className="font-mono text-echo-muted w-10 flex-shrink-0">
                  #{entry.loop_number}
                </span>
                <span className="text-echo-text/70 font-story flex-1 truncate">
                  {entry.summary}
                </span>
                <span>
                  {entry.status === "broken" ? (
                    <span className="text-echo-success">{"\u2713"}</span>
                  ) : (
                    <span className="text-echo-danger">{"\u2620"}</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Action buttons */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2 }}
          className="flex flex-wrap items-center justify-center gap-3"
        >
          <button
            onClick={() => exportStoryPDF()}
            className="px-5 py-2.5 rounded-xl bg-echo-panel border border-echo-border text-echo-text font-display font-semibold text-sm hover:border-echo-accent/50 transition-all"
          >
            Export Story
          </button>
          <button
            onClick={handlePlayAgain}
            className="px-5 py-2.5 rounded-xl bg-echo-accent/20 border border-echo-accent/40 text-echo-accent font-display font-semibold text-sm hover:bg-echo-accent/30 transition-all"
          >
            Play Again
          </button>
          <button
            onClick={handleNewScenario}
            className="px-5 py-2.5 rounded-xl bg-echo-accent text-white font-display font-semibold text-sm hover:bg-echo-accent/90 glow-accent transition-all"
          >
            New Scenario
          </button>
        </motion.div>
      </div>
    </motion.div>
  );
}
