import { motion } from "framer-motion";
import { useGameStore } from "../store/gameStore";

export default function LoopTimer() {
  const timerSeconds = useGameStore((s) => s.timerSeconds);
  const gameState = useGameStore((s) => s.gameState);

  const totalSeconds = gameState?.loop_duration_seconds ?? 300;
  const progress = totalSeconds > 0 ? timerSeconds / totalSeconds : 1;

  const minutes = Math.floor(Math.max(0, timerSeconds) / 60);
  const seconds = Math.max(0, timerSeconds) % 60;
  const timeStr = `${minutes}:${seconds.toString().padStart(2, "0")}`;

  const isWarning = timerSeconds <= 120 && timerSeconds > 60;
  const isDanger = timerSeconds <= 60 && timerSeconds > 30;
  const isCritical = timerSeconds <= 30;

  const ringColor = isCritical || isDanger
    ? "#ff4757"
    : isWarning
      ? "#f5a623"
      : "#7c6ff5";

  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - progress);

  return (
    <motion.div
      className="relative flex items-center justify-center"
      animate={
        isCritical
          ? { scale: [1, 1.08, 1] }
          : isDanger
            ? { scale: [1, 1.04, 1] }
            : {}
      }
      transition={
        isCritical
          ? { duration: 0.5, repeat: Infinity }
          : isDanger
            ? { duration: 1, repeat: Infinity }
            : {}
      }
    >
      <svg width="80" height="80" className="transform -rotate-90">
        {/* Background ring */}
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke="#2a2a40"
          strokeWidth="4"
        />
        {/* Progress ring */}
        <motion.circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke={ringColor}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          animate={{ strokeDashoffset }}
          transition={{ duration: 0.5 }}
        />
      </svg>

      {/* Time display */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span
          className="font-mono text-sm font-bold"
          style={{ color: ringColor }}
        >
          {timeStr}
        </span>
      </div>

      {/* Pulse ring on critical */}
      {isCritical && (
        <motion.div
          className="absolute inset-0 rounded-full border-2"
          style={{ borderColor: ringColor }}
          animate={{ scale: [1, 1.4], opacity: [0.6, 0] }}
          transition={{ duration: 1, repeat: Infinity }}
        />
      )}
    </motion.div>
  );
}
