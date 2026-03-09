import { motion } from "framer-motion";
import { useGameStore } from "../store/gameStore";

interface VoiceOrbProps {
  onStartRecording: () => void;
  onStopRecording: () => void;
}

export default function VoiceOrb({
  onStartRecording,
  onStopRecording,
}: VoiceOrbProps) {
  const isRecording = useGameStore((s) => s.isRecording);
  const isNarratorSpeaking = useGameStore((s) => s.isNarratorSpeaking);

  const handleClick = () => {
    if (isRecording) {
      onStopRecording();
    } else {
      onStartRecording();
    }
  };

  return (
    <motion.button
      onClick={handleClick}
      whileTap={{ scale: 0.9 }}
      className={`relative w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300
        ${
          isRecording
            ? "bg-echo-danger/20 border-2 border-echo-danger"
            : isNarratorSpeaking
              ? "bg-echo-accent/20 border-2 border-echo-accent animate-pulse-glow"
              : "bg-echo-panel border-2 border-echo-border hover:border-echo-accent/50"
        }
      `}
      title={isRecording ? "Stop recording" : "Start recording"}
    >
      {/* Mic icon */}
      <svg
        className={`w-5 h-5 ${isRecording ? "text-echo-danger" : "text-echo-muted"}`}
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        {isRecording ? (
          <rect x="6" y="6" width="12" height="12" rx="2" />
        ) : (
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1 1.93c-3.94-.49-7-3.85-7-7.93h2c0 3.31 2.69 6 6 6s6-2.69 6-6h2c0 4.08-3.06 7.44-7 7.93V20h4v2H8v-2h4v-4.07z" />
        )}
      </svg>

      {/* Recording indicator ring */}
      {isRecording && (
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-echo-danger"
          animate={{ scale: [1, 1.3, 1], opacity: [1, 0, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      )}

      {/* Narrator speaking waves */}
      {isNarratorSpeaking && !isRecording && (
        <>
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="absolute inset-0 rounded-full border border-echo-accent/30"
              animate={{ scale: [1, 1.5 + i * 0.2], opacity: [0.4, 0] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: i * 0.3,
              }}
            />
          ))}
        </>
      )}
    </motion.button>
  );
}
