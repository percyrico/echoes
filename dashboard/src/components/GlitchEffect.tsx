import { motion } from "framer-motion";

interface GlitchEffectProps {
  active: boolean;
  intensity?: "low" | "medium" | "high";
}

export default function GlitchEffect({
  active,
  intensity = "medium",
}: GlitchEffectProps) {
  if (!active) return null;

  const opacityMap = {
    low: 0.3,
    medium: 0.5,
    high: 0.8,
  };

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 50 }}>
      {/* Scanlines */}
      <div className="absolute inset-0 scanlines" style={{ opacity: opacityMap[intensity] }} />

      {/* Color shift bands */}
      <motion.div
        className="absolute inset-0"
        animate={{
          backgroundPosition: ["0% 0%", "0% 100%"],
        }}
        transition={{ duration: 0.1, repeat: Infinity, repeatType: "mirror" }}
        style={{
          background:
            "repeating-linear-gradient(0deg, transparent 0%, transparent 95%, rgba(124, 111, 245, 0.1) 95%, rgba(124, 111, 245, 0.1) 100%)",
          backgroundSize: "100% 20px",
          mixBlendMode: "screen",
        }}
      />

      {/* Horizontal offset bands */}
      {intensity !== "low" && (
        <>
          <motion.div
            className="absolute left-0 right-0 h-1 bg-echo-accent/20"
            animate={{
              top: ["10%", "90%", "30%", "70%", "50%"],
              scaleX: [1, 1.02, 0.98, 1.01, 1],
            }}
            transition={{ duration: 0.3, repeat: Infinity }}
          />
          <motion.div
            className="absolute left-0 right-0 h-0.5 bg-echo-danger/20"
            animate={{
              top: ["80%", "20%", "60%", "40%", "50%"],
              scaleX: [0.98, 1.03, 1, 0.97, 1],
            }}
            transition={{ duration: 0.25, repeat: Infinity }}
          />
        </>
      )}

      {/* Color aberration overlay */}
      {intensity === "high" && (
        <motion.div
          className="absolute inset-0"
          animate={{ opacity: [0, 0.15, 0, 0.1, 0] }}
          transition={{ duration: 0.2, repeat: Infinity }}
          style={{
            background:
              "linear-gradient(90deg, rgba(255,0,0,0.1) 0%, transparent 33%, rgba(0,255,0,0.1) 66%, rgba(0,0,255,0.1) 100%)",
            mixBlendMode: "screen",
          }}
        />
      )}
    </div>
  );
}
