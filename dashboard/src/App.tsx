import { useGameStore } from "./store/gameStore";
import ScenarioLobby from "./components/ScenarioLobby";
import GameView from "./components/GameView";
import LoopFailScreen from "./components/LoopFailScreen";
import VictoryScreen from "./components/VictoryScreen";

export default function App() {
  const view = useGameStore((s) => s.view);
  return (
    <div className="h-screen w-screen overflow-hidden bg-echo-bg">
      {view === "lobby" && <ScenarioLobby />}
      {view === "game" && <GameView />}
      {view === "loop_fail" && <LoopFailScreen />}
      {view === "victory" && <VictoryScreen />}
    </div>
  );
}
