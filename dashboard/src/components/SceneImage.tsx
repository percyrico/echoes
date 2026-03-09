import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useGameStore } from "../store/gameStore";
import type { Mood } from "../types";

const MOOD_OVERLAYS: Record<Mood, string> = {
  mysterious: "rgba(124, 111, 245, 0.15)",
  tense: "rgba(200, 100, 255, 0.12)",
  urgent: "rgba(255, 71, 87, 0.18)",
  dread: "rgba(40, 20, 60, 0.25)",
  calm: "rgba(80, 140, 255, 0.12)",
  revelation: "rgba(245, 200, 35, 0.15)",
};

export default function SceneImage() {
  const sceneImageUrl = useGameStore((s) => s.sceneImageUrl);
  const mood = useGameStore((s) => s.currentMood);
  const [currentImg, setCurrentImg] = useState<string | null>(null);
  const [nextImg, setNextImg] = useState<string | null>(null);
  const [showNext, setShowNext] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const preloadRef = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    if (!sceneImageUrl || sceneImageUrl === currentImg) return;

    // Preload the new image, then crossfade
    setIsLoading(true);
    const img = new Image();
    preloadRef.current = img;
    img.onload = () => {
      setNextImg(sceneImageUrl);
      setShowNext(true);
      setIsLoading(false);
      // After crossfade completes, swap
      setTimeout(() => {
        setCurrentImg(sceneImageUrl);
        setNextImg(null);
        setShowNext(false);
      }, 800);
    };
    img.onerror = () => {
      setIsLoading(false);
    };
    img.src = sceneImageUrl;

    return () => {
      preloadRef.current = null;
    };
  }, [sceneImageUrl, currentImg]);

  const overlayColor = MOOD_OVERLAYS[mood];

  return (
    <div className="relative w-full h-64 md:h-80 lg:h-96 rounded-xl overflow-hidden bg-echo-surface">
      {/* Mood overlay */}
      <div
        className="absolute inset-0 z-10 pointer-events-none"
        style={{ backgroundColor: overlayColor }}
      />

      {/* Current image (bottom layer) */}
      {currentImg ? (
        <motion.img
          key={currentImg}
          src={currentImg}
          alt="Scene"
          className="absolute inset-0 w-full h-full object-cover"
          animate={{ scale: [1, 1.05] }}
          transition={{
            duration: 15,
            repeat: Infinity,
            repeatType: "reverse",
            ease: "linear",
          }}
        />
      ) : (
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{
            background:
              "radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a12 70%)",
          }}
        >
          <div className="text-echo-muted/40 text-sm font-display">
            Scene materializing...
          </div>
        </div>
      )}

      {/* Next image (top layer, fades in for crossfade) */}
      {nextImg && (
        <motion.img
          src={nextImg}
          alt="Scene"
          className="absolute inset-0 w-full h-full object-cover z-[5]"
          initial={{ opacity: 0 }}
          animate={{ opacity: showNext ? 1 : 0 }}
          transition={{ duration: 0.8 }}
        />
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute inset-0 z-20 flex items-center justify-center">
          <motion.div
            className="w-8 h-8 border-2 border-echo-accent/30 border-t-echo-accent rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          />
        </div>
      )}

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-echo-bg to-transparent z-10 pointer-events-none" />
    </div>
  );
}
