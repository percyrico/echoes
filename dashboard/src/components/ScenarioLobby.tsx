import { useState } from "react";
import { motion } from "framer-motion";
import { useGameStore } from "../store/gameStore";
import { useWebSocket } from "../hooks/useWebSocket";
import MoodParticles from "./MoodParticles";
import type { Scenario, ScenarioInfo } from "../types";

const SCENARIOS: ScenarioInfo[] = [
  {
    id: "last_train",
    name: "The Last Train",
    description:
      "You board the midnight express. The passengers are familiar. The destination never comes. Something happened on this train -- you just can't remember what.",
    difficulty: "\u25CF\u25CF\u25CB",
    estimated_loops: "~8 loops",
  },
  {
    id: "locked_room",
    name: "The Locked Room",
    description:
      "You wake in a sealed chamber with four strangers. A clock counts down. One of you holds the key -- but trust is a luxury none can afford.",
    difficulty: "\u25CF\u25CF\u25CF",
    estimated_loops: "~10 loops",
  },
  {
    id: "dinner_party",
    name: "The Dinner Party",
    description:
      "An elegant gathering at a remote estate. The host has a secret. The wine is poured. By midnight, someone will die -- and it's happened before.",
    difficulty: "\u25CF\u25CF\u25CB",
    estimated_loops: "~7 loops",
  },
  {
    id: "the_signal",
    name: "The Signal",
    description:
      "A deep-space research station has gone silent. You're the only one awake. The signal it received is changing the station -- and you.",
    difficulty: "\u25CF\u25CF\u25CF",
    estimated_loops: "~12 loops",
  },
  {
    id: "the_crash",
    name: "The Crash",
    description:
      "A private plane went down in the mountains. All four passengers survived \u2014 but only three walked away. Someone sabotaged the aircraft.",
    difficulty: "\u25CF\u25CF\u25CB",
    estimated_loops: "~8 loops",
  },
  {
    id: "the_heist",
    name: "The Heist",
    description:
      "A priceless diamond vanished during a museum gala. The lead security guard lies unconscious. The thief is still in the building \u2014 and the lockdown is ticking.",
    difficulty: "\u25CF\u25CF\u25CF",
    estimated_loops: "~10 loops",
  },
  {
    id: "room_414",
    name: "Room 414",
    description:
      "A tech CEO found dead in a luxury hotel room. The police say suicide. The evidence says otherwise. Someone in this hotel is lying.",
    difficulty: "\u25CF\u25CF\u25CB",
    estimated_loops: "~8 loops",
  },
  {
    id: "the_factory",
    name: "The Factory",
    description:
      "An explosion at a chemical plant killed three workers. The company blames equipment failure. But someone disabled the safety systems \u2014 and someone else was paid to look away.",
    difficulty: "\u25CF\u25CF\u25CF",
    estimated_loops: "~10 loops",
  },
];

const SCENARIO_ICONS: Record<Scenario, string> = {
  last_train: "\u{1F682}",
  locked_room: "\u{1F512}",
  dinner_party: "\u{1F377}",
  the_signal: "\u{1F4E1}",
  the_crash: "✈️",
  the_heist: "💎",
  room_414: "🔑",
  the_factory: "🏭",
};

const SCENARIO_GRADIENTS: Record<Scenario, string> = {
  last_train:
    "linear-gradient(135deg, rgba(60,40,100,0.4) 0%, rgba(30,20,60,0.6) 100%)",
  locked_room:
    "linear-gradient(135deg, rgba(80,30,30,0.4) 0%, rgba(40,15,15,0.6) 100%)",
  dinner_party:
    "linear-gradient(135deg, rgba(80,50,20,0.4) 0%, rgba(40,25,10,0.6) 100%)",
  the_signal:
    "linear-gradient(135deg, rgba(20,50,80,0.4) 0%, rgba(10,25,50,0.6) 100%)",
  the_crash:
    "linear-gradient(135deg, rgba(40,60,80,0.4) 0%, rgba(20,30,50,0.6) 100%)",
  the_heist:
    "linear-gradient(135deg, rgba(60,20,80,0.4) 0%, rgba(30,10,50,0.6) 100%)",
  room_414:
    "linear-gradient(135deg, rgba(80,60,30,0.4) 0%, rgba(50,35,15,0.6) 100%)",
  the_factory:
    "linear-gradient(135deg, rgba(80,30,30,0.4) 0%, rgba(40,15,15,0.6) 100%)",
};

export default function ScenarioLobby() {
  const [selected, setSelected] = useState<Scenario | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [playerName, setPlayerNameLocal] = useState("");
  const setScenario = useGameStore((s) => s.setScenario);
  const setView = useGameStore((s) => s.setView);
  const setPlayerName = useGameStore((s) => s.setPlayerName);
  const { connect, sendJSON } = useWebSocket();

  const handleStart = () => {
    if (!selected || !playerName.trim()) return;
    setIsStarting(true);
    setScenario(selected);
    setPlayerName(playerName.trim());
    connect(() => {
      sendJSON({ type: "start_game", scenario: selected, player_name: playerName.trim() });
      setView("game");
    });
  };

  return (
    <div className="relative h-full w-full flex flex-col items-center overflow-hidden">
      {/* Background particles */}
      <MoodParticles mood="mysterious" />

      {/* Radial gradient background */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at 50% 30%, rgba(124,111,245,0.08) 0%, transparent 60%)",
        }}
      />

      <div className="relative z-10 flex flex-col items-center h-full w-full px-4 py-3 md:py-4 max-w-6xl mx-auto">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center shrink-0"
        >
          <div className="relative inline-block">
            <h1 className="text-3xl md:text-4xl lg:text-5xl font-display font-bold text-echo-text tracking-wider">
              ECHOES
            </h1>
            {/* Ripple rings behind title */}
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 border border-echo-accent/20 rounded-full pointer-events-none"
                style={{ width: 150 + i * 50, height: 60 + i * 15 }}
                animate={{
                  scale: [1, 1.3],
                  opacity: [0.3, 0],
                }}
                transition={{
                  duration: 2.5,
                  repeat: Infinity,
                  delay: i * 0.8,
                }}
              />
            ))}
          </div>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="text-echo-muted font-story text-xs md:text-sm italic mt-1"
          >
            Every loop reveals the truth
          </motion.p>
        </motion.div>

        {/* Scenario grid — fills available space */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 w-full flex-1 mt-3 md:mt-4 min-h-0 auto-rows-fr"
          style={{ maxHeight: "calc(100vh - 240px)" }}
        >
          {SCENARIOS.map((scenario, i) => {
            const isSelected = selected === scenario.id;
            return (
              <motion.button
                key={scenario.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.05, duration: 0.4 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setSelected(scenario.id)}
                className={`relative text-left p-3 md:p-4 rounded-xl border transition-all duration-300 overflow-hidden flex flex-col ${
                  isSelected
                    ? "border-echo-accent glow-accent"
                    : "border-echo-border hover:border-echo-accent/30"
                }`}
                style={{
                  background: SCENARIO_GRADIENTS[scenario.id],
                }}
              >
                {/* Selection ring */}
                {isSelected && (
                  <motion.div
                    className="absolute inset-0 rounded-xl border-2 border-echo-accent pointer-events-none"
                    layoutId="selection-ring"
                    transition={{ type: "spring", damping: 25, stiffness: 300 }}
                  />
                )}

                <div className="flex items-center gap-2 mb-1 md:mb-2">
                  <span className="text-2xl md:text-3xl">{SCENARIO_ICONS[scenario.id]}</span>
                  <h3 className="text-echo-text font-display font-semibold text-sm md:text-base leading-tight">
                    {scenario.name}
                  </h3>
                </div>
                <p className="text-echo-muted text-xs md:text-sm font-story leading-snug flex-1 line-clamp-3 md:line-clamp-4">
                  {scenario.description}
                </p>
                <div className="flex items-center gap-2 text-xs text-echo-muted/80 font-mono mt-1 md:mt-2">
                  <span title="Difficulty">{scenario.difficulty}</span>
                  <span className="text-echo-border">|</span>
                  <span>{scenario.estimated_loops}</span>
                </div>
              </motion.button>
            );
          })}
        </motion.div>

        {/* Bottom bar: name input + start button */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.5 }}
          className="shrink-0 flex flex-col sm:flex-row items-center gap-3 mt-3 md:mt-4 w-full max-w-lg"
        >
          <input
            id="player-name"
            type="text"
            value={playerName}
            onChange={(e) => setPlayerNameLocal(e.target.value)}
            placeholder="Enter your name..."
            maxLength={30}
            className="w-full sm:flex-1 px-4 py-2.5 rounded-xl bg-echo-surface border border-echo-border text-echo-text placeholder-echo-muted font-story text-sm md:text-base outline-none focus:border-echo-accent/60 transition-colors duration-300"
          />
          <button
            onClick={handleStart}
            disabled={!selected || !playerName.trim() || isStarting}
            className={`w-full sm:w-auto px-6 py-2.5 rounded-xl font-display font-semibold text-sm md:text-base transition-all duration-300 whitespace-nowrap ${
              selected && playerName.trim()
                ? "bg-echo-accent text-white hover:bg-echo-accent/90 glow-accent cursor-pointer"
                : "bg-echo-panel text-echo-muted border border-echo-border cursor-not-allowed"
            }`}
          >
            {isStarting ? (
              <span className="flex items-center justify-center gap-2">
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                />
                Entering...
              </span>
            ) : (
              "Enter the Loop \u2192"
            )}
          </button>
        </motion.div>
      </div>
    </div>
  );
}
