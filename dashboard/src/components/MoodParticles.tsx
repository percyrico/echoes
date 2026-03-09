import { useEffect, useRef } from "react";
import type { Mood } from "../types";

interface MoodConfig {
  count: number;
  speed: number;
  size: [number, number];
  color: string;
  direction: "up" | "down" | "float";
  opacity: number;
}

const MOOD_CONFIGS: Record<Mood, MoodConfig> = {
  mysterious: {
    count: 40,
    speed: 0.3,
    size: [1, 3],
    color: "168, 130, 255",
    direction: "float",
    opacity: 0.4,
  },
  tense: {
    count: 60,
    speed: 0.8,
    size: [1, 2],
    color: "200, 180, 255",
    direction: "float",
    opacity: 0.3,
  },
  urgent: {
    count: 80,
    speed: 1.5,
    size: [1, 4],
    color: "255, 71, 87",
    direction: "up",
    opacity: 0.5,
  },
  dread: {
    count: 30,
    speed: 0.15,
    size: [2, 5],
    color: "80, 60, 120",
    direction: "down",
    opacity: 0.6,
  },
  calm: {
    count: 25,
    speed: 0.2,
    size: [1, 3],
    color: "100, 160, 255",
    direction: "float",
    opacity: 0.3,
  },
  revelation: {
    count: 70,
    speed: 1.0,
    size: [1, 3],
    color: "245, 166, 35",
    direction: "up",
    opacity: 0.6,
  },
};

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  life: number;
}

interface MoodParticlesProps {
  mood: Mood;
}

export default function MoodParticles({ mood }: MoodParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animRef = useRef<number>(0);
  const configRef = useRef<MoodConfig>(MOOD_CONFIGS[mood]);

  useEffect(() => {
    configRef.current = MOOD_CONFIGS[mood];
  }, [mood]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const createParticle = (): Particle => {
      const cfg = configRef.current;
      const size = cfg.size[0]! + Math.random() * (cfg.size[1]! - cfg.size[0]!);
      return {
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * cfg.speed,
        vy:
          cfg.direction === "up"
            ? -Math.random() * cfg.speed
            : cfg.direction === "down"
              ? Math.random() * cfg.speed * 0.5
              : (Math.random() - 0.5) * cfg.speed * 0.5,
        size,
        opacity: Math.random() * cfg.opacity,
        life: Math.random(),
      };
    };

    particlesRef.current = Array.from(
      { length: configRef.current.count },
      createParticle,
    );

    const animate = () => {
      const cfg = configRef.current;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Adjust particle count
      while (particlesRef.current.length < cfg.count) {
        particlesRef.current.push(createParticle());
      }
      while (particlesRef.current.length > cfg.count) {
        particlesRef.current.pop();
      }

      for (const p of particlesRef.current) {
        p.x += p.vx;
        p.y += p.vy;
        p.life += 0.002;

        if (cfg.direction === "float") {
          p.vy += Math.sin(p.life * 2) * 0.01;
        }

        // Wrap around
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        const alpha = p.opacity * (0.5 + 0.5 * Math.sin(p.life * 3));
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${cfg.color}, ${alpha})`;
        ctx.fill();
      }

      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 1 }}
    />
  );
}
