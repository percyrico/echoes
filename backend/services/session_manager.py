"""SessionManager — Core game engine for Echoes time-loop mystery."""

import asyncio
import os
import re
import time
from typing import Optional

from fastapi import WebSocket

from models.schemas import (
    Scenario, GameState, LoopStatus, LoopEntry, Clue, Mood,
)
from models.scenarios import get_scenario_config
from services.gemini_live import GeminiLiveSession
from services.clue_detector import ClueDetector
from services.image_gen import ImageGenerator
from services.world_db import WorldDB
from agents.composer import get_audio_cue


class SessionManager:
    """Manages active game sessions, Gemini Live connections, and game logic."""

    def __init__(self, db: WorldDB):
        self.db = db
        self.game_states: dict[str, GameState] = {}
        self.live_sessions: dict[str, GeminiLiveSession] = {}
        self.clue_detectors: dict[str, ClueDetector] = {}
        self.websockets: dict[str, WebSocket] = {}
        self._loop_timers: dict[str, asyncio.Task] = {}
        self._timer_update_tasks: dict[str, asyncio.Task] = {}
        self.api_key = os.getenv("GOOGLE_API_KEY", "")
        self.image_gen = ImageGenerator(self.api_key)

    async def get_or_create(self, session_id: str, scenario: Scenario) -> GameState:
        """Get existing game state or create a new one."""
        if session_id in self.game_states:
            return self.game_states[session_id]

        # Check DB
        db_session = await self.db.get_session(session_id)
        if db_session:
            state = GameState(**db_session["game_state"])
            self.game_states[session_id] = state
            return state

        # Create new
        config = get_scenario_config(scenario)
        state = GameState(
            session_id=session_id,
            scenario=scenario,
            loop_duration_seconds=config["loop_duration_seconds"],
            total_clues_needed=config.get("key_clues_needed", 5),
            characters=list(config["characters"]),
            current_mood=config["initial_mood"],
        )
        self.game_states[session_id] = state

        # Save to DB
        await self.db.save_session(
            session_id, scenario.value, state.to_dict()
        )

        return state

    async def start_game(self, session_id: str, scenario: Scenario, websocket: WebSocket, player_name: str = "Detective"):
        """Initialize a new game session and start the first loop."""
        state = await self.get_or_create(session_id, scenario)
        state.player_name = player_name
        self.websockets[session_id] = websocket

        # Create clue detector
        self.clue_detectors[session_id] = ClueDetector(scenario, self.api_key)

        # Send initial game state
        await websocket.send_json({
            "type": "game_state",
            "data": state.to_dict(),
        })

        # Send initial audio cue
        config = get_scenario_config(scenario)
        audio_cue = get_audio_cue(config["initial_mood"], scenario.value)
        await websocket.send_json({
            "type": "audio_cue",
            "data": audio_cue.model_dump(),
        })

        # Generate scene image in background
        asyncio.create_task(
            self._generate_scene_image(session_id, state)
        )

    async def start_loop(self, session_id: str, websocket: WebSocket):
        """Start or restart the current loop with timer and Gemini Live."""
        state = self.game_states.get(session_id)
        if not state:
            return

        self.websockets[session_id] = websocket

        # Set loop as active
        state.loop_status = LoopStatus.ACTIVE
        state.loop_start_time = time.time()

        # Build system prompt with loop history
        system_prompt = self._build_system_prompt(state)

        # Connect Gemini Live
        live = GeminiLiveSession(state.scenario, self.api_key)
        self.live_sessions[session_id] = live

        # Start loop timer
        self._start_loop_timer(session_id, state.loop_duration_seconds)

        # Start periodic timer updates
        self._start_timer_updates(session_id)

        try:
            print(f"[SessionManager] Connecting Gemini Live for {session_id}, loop {state.current_loop}...", flush=True)
            await live.connect(system_prompt)
            print(f"[SessionManager] Gemini Live connected!", flush=True)

            # Send opening prompt
            config = get_scenario_config(state.scenario)
            player_name = state.player_name
            opening = (
                f"Begin loop {state.current_loop}. "
                f"FIRST, briefly introduce the scenario to the player: the name is '{config['name']}' and the premise is: {config['description']}. "
                f"Start by saying something like 'Welcome to {config['name']}, {player_name}.' followed by a one-sentence summary of the situation. "
                f"THEN set the scene: {config['opening_narration']} "
                "Speak directly — you are narrating aloud. "
                "Speak 3-5 clear sentences. ALWAYS finish your last sentence completely — never stop mid-word. "
                f"The player's name is {player_name}. You may use their name ONCE in the opening greeting, then only sparingly — most turns should NOT include their name. "
                "End with a short, varied question prompting the player to act."
            )
            if state.current_loop > 1:
                opening = (
                    f"This is loop {state.current_loop}. The player has been through this before. "
                    f"Reference their past experiences subtly. They know something is wrong. "
                    f"Begin the loop again but acknowledge the déjà vu. "
                    "Speak 3-5 clear sentences. ALWAYS finish your last sentence — never stop mid-word. "
                    f"The player's name is {player_name}. Use their name sparingly — at most once every 3-4 turns. "
                    "End with a short, varied question prompting the player to act."
                )

            await live.send_text(opening)

            # Set up transcript processing
            turn_text_buffer: list[str] = []
            processed_text_length: list[int] = [0]
            image_triggered: list[bool] = [False]
            pending_image_task: list[asyncio.Task | None] = [None]

            async def on_response(response: dict):
                if response["type"] == "audio":
                    try:
                        await websocket.send_json({
                            "type": "live_audio",
                            "data": response.get("data", ""),
                            "mime_type": response.get("mime_type", ""),
                        })
                    except Exception:
                        pass

                elif response["type"] == "text":
                    text = response["data"]
                    turn_text_buffer.append(text)

                    # Send transcript text to client
                    try:
                        await websocket.send_json({
                            "type": "transcript_text",
                            "data": text,
                        })
                    except Exception:
                        pass

                    # Trigger scene image early (on first ~80 chars)
                    current_text = "".join(turn_text_buffer)
                    if not image_triggered[0] and len(current_text) >= 80:
                        image_triggered[0] = True
                        # Cancel any previous pending image task
                        if pending_image_task[0] and not pending_image_task[0].done():
                            pending_image_task[0].cancel()
                        pending_image_task[0] = asyncio.create_task(
                            self._update_scene_image(session_id, current_text)
                        )

                    # Process incrementally for clue detection
                    new_chars = len(current_text) - processed_text_length[0]

                    if new_chars >= 150:
                        unprocessed = current_text[processed_text_length[0]:]
                        for sep in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                            last_sep = unprocessed.rfind(sep)
                            if last_sep > 50:
                                chunk = unprocessed[:last_sep + 1].strip()
                                processed_text_length[0] += last_sep + len(sep)
                                asyncio.create_task(
                                    self._process_transcript_chunk(session_id, chunk)
                                )
                                break

                elif response["type"] == "turn_complete":
                    full_text = "".join(turn_text_buffer).strip()

                    # Check if the narrator was cut off (no ending punctuation or question)
                    was_cut_off = (
                        len(full_text) > 20
                        and not full_text.rstrip().endswith("?")
                        and not full_text.rstrip().endswith(".")
                        and not full_text.rstrip().endswith("!")
                    )

                    if was_cut_off:
                        # Don't signal turn complete to frontend — narrator is still going
                        print(f"[SessionManager] Narrator cut off, auto-continuing...", flush=True)
                        # Ask the model to finish its thought
                        await live.send_text(
                            "You were cut off mid-sentence. Finish your thought in 1-2 short sentences, "
                            "then ask the player what to do next."
                        )
                        # Don't clear the buffer — keep accumulating
                    else:
                        # Normal turn complete
                        try:
                            await websocket.send_json({"type": "live_turn_complete", "data": ""})
                        except Exception:
                            pass

                        # Process remaining text
                        remaining = full_text[processed_text_length[0]:].strip()
                        if remaining:
                            asyncio.create_task(
                                self._process_transcript_chunk(session_id, remaining)
                            )

                        # Reset image trigger for next turn
                        image_triggered[0] = False

                        # Generate choices for the player
                        asyncio.create_task(
                            self._generate_choices(session_id, full_text)
                        )

                        turn_text_buffer.clear()
                        processed_text_length[0] = 0

                elif response["type"] == "error":
                    print(f"Live error: {response.get('data', '')}", flush=True)

            await live.receive_responses(on_response)

        except asyncio.CancelledError:
            print(f"[SessionManager] Live task cancelled for {session_id}", flush=True)
            await live.disconnect()
        except Exception as e:
            print(f"Live session error for {session_id}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            await live.disconnect()

    def _build_system_prompt(self, state: GameState) -> str:
        """Build the full system prompt including loop history and clues."""
        config = get_scenario_config(state.scenario)
        template = config["system_prompt"]

        # Build loop history summary
        loop_history_parts = []
        for entry in state.loop_history:
            actions = ", ".join(entry.actions_taken[:5]) if entry.actions_taken else "none recorded"
            clues = ", ".join(entry.clues_found) if entry.clues_found else "none"
            loop_history_parts.append(
                f"Loop {entry.loop_number} ({entry.status.value}): "
                f"Duration {entry.duration_seconds:.0f}s. "
                f"Actions: {actions}. "
                f"Clues found: {clues}. "
                f"Ended: {entry.death_description or 'timer expired'}"
            )
        loop_history_str = "\n".join(loop_history_parts) if loop_history_parts else "This is the first loop."

        # Build clues found summary
        clues_found_parts = []
        for clue in state.clues:
            key_marker = " [KEY]" if clue.is_key_clue else ""
            clues_found_parts.append(
                f"- {clue.text}{key_marker}: {clue.detail} (found in loop {clue.loop_discovered})"
            )
        clues_found_str = "\n".join(clues_found_parts) if clues_found_parts else "No clues found yet."

        # Calculate time remaining
        time_remaining = f"{state.loop_duration_seconds // 60} minutes"

        # Check if player can break the loop
        key_clues = sum(1 for c in state.clues if c.is_key_clue)
        can_break = "Yes" if state.can_break_loop else f"No (need {state.total_clues_needed - key_clues} more key clues)"

        # Fill template
        prompt = template.format(
            loop_history=loop_history_str,
            clues_found=clues_found_str,
            current_loop=state.current_loop,
            time_remaining=time_remaining,
            can_break=can_break,
            player_name=state.player_name,
        )

        return prompt

    async def _process_transcript_chunk(self, session_id: str, text: str):
        """Process a transcript chunk through clue detection."""
        state = self.game_states.get(session_id)
        detector = self.clue_detectors.get(session_id)
        ws = self.websockets.get(session_id)

        if not state or not detector or not ws:
            return

        text = self._clean_transcript(text)
        if not text or len(text) < 30:
            return

        try:
            result = await detector.analyze(text, state)

            # Process new clues
            for clue_data in result.get("new_clues", []):
                clue = Clue(
                    text=clue_data["text"],
                    detail=clue_data.get("detail", ""),
                    loop_discovered=state.current_loop,
                    is_key_clue=clue_data.get("is_key_clue", False),
                )

                # Check if clue already exists
                existing_texts = {c.text.lower() for c in state.clues}
                if clue.text.lower() not in existing_texts:
                    state.clues.append(clue)

                    # Generate clue image in background
                    asyncio.create_task(
                        self._generate_clue_image(session_id, clue)
                    )

                    # Send clue discovery to client
                    try:
                        await ws.send_json({
                            "type": "clue_discovered",
                            "data": clue.model_dump(mode="json"),
                        })
                    except Exception:
                        pass

                    print(f"[SessionManager] New clue: {clue.text} (key={clue.is_key_clue})", flush=True)

            # Update mood if changed
            new_mood_str = result.get("mood", state.current_mood.value)
            try:
                new_mood = Mood(new_mood_str)
                if new_mood != state.current_mood:
                    state.current_mood = new_mood
                    audio_cue = get_audio_cue(new_mood, state.scenario.value)
                    try:
                        await ws.send_json({
                            "type": "mood_change",
                            "data": {"mood": new_mood.value},
                        })
                        await ws.send_json({
                            "type": "audio_cue",
                            "data": audio_cue.model_dump(),
                        })
                    except Exception:
                        pass
            except ValueError:
                pass

            # Track actions
            for action in result.get("actions", []):
                if state.loop_history:
                    current_entry = None
                    for entry in state.loop_history:
                        if entry.loop_number == state.current_loop:
                            current_entry = entry
                            break
                    if current_entry:
                        current_entry.actions_taken.append(action)

            # Check can_break status
            key_clues = sum(1 for c in state.clues if c.is_key_clue)
            if key_clues >= state.total_clues_needed:
                if not state.can_break_loop:
                    state.can_break_loop = True
                    try:
                        await ws.send_json({
                            "type": "can_break_loop",
                            "data": {"can_break": True, "key_clues": key_clues},
                        })
                    except Exception:
                        pass

            # Check for explicit can_break from analysis
            if result.get("can_break", False) and state.can_break_loop:
                await self._handle_loop_break(session_id)
                return

            # Check should_fail
            if result.get("should_fail", False):
                death_desc = "A fatal action was taken."
                if result.get("actions"):
                    death_desc = result["actions"][-1]
                await self._handle_loop_fail(session_id, death_desc)

            # Persist state
            await self.db.save_session(
                session_id, state.scenario.value, state.to_dict()
            )

        except Exception as e:
            print(f"Transcript processing error: {e}", flush=True)
            import traceback
            traceback.print_exc()

    def _start_loop_timer(self, session_id: str, duration_seconds: int):
        """Start a countdown timer that triggers loop failure."""
        # Cancel existing timer
        old_timer = self._loop_timers.pop(session_id, None)
        if old_timer and not old_timer.done():
            old_timer.cancel()

        async def _timer_expire():
            await asyncio.sleep(duration_seconds)
            state = self.game_states.get(session_id)
            scenario_name = state.scenario.value if state else "unknown"
            death_messages = {
                "last_train": "The train pulls into the station. The doors open. The truth walks away with the passengers. Time folds back.",
                "locked_room": "The clock strikes twelve. The room seals itself again. The answers slip through your fingers like smoke.",
                "dinner_party": "The dessert is served. The poison takes hold. You were too late. The candles flicker and die.",
                "the_signal": "The signal reaches full power. The station shudders. Your vision fractures. Emergency lights pulse red. Again.",
                "the_crash": "The federal team arrives in black SUVs. They take over the scene. The evidence goes cold. Snow covers the truth.",
                "the_heist": "The lockdown lifts. The thief walks free among the guests. The diamond stays hidden. The museum doors open.",
                "room_414": "The hotel lawyer arrives with a court order. The crime scene is sealed. The killer checks out. Case closed — incorrectly.",
                "the_factory": "The company lawyers descend. Access is restricted. The falsified records replace the real ones. Three families get no justice.",
            }
            death_desc = death_messages.get(scenario_name, "Time ran out. The loop resets.")
            await self._handle_loop_fail(session_id, death_desc)

        self._loop_timers[session_id] = asyncio.create_task(_timer_expire())

    def _start_timer_updates(self, session_id: str):
        """Send periodic timer updates to the client."""
        old_task = self._timer_update_tasks.pop(session_id, None)
        if old_task and not old_task.done():
            old_task.cancel()

        async def _send_updates():
            while True:
                await asyncio.sleep(1)
                state = self.game_states.get(session_id)
                ws = self.websockets.get(session_id)
                if not state or not ws or state.loop_status != LoopStatus.ACTIVE:
                    break
                if state.loop_start_time:
                    elapsed = time.time() - state.loop_start_time
                    remaining = max(0, state.loop_duration_seconds - elapsed)
                    try:
                        await ws.send_json({
                            "type": "timer_update",
                            "data": {
                                "seconds": int(remaining),
                                "remaining_seconds": int(remaining),
                                "total_seconds": state.loop_duration_seconds,
                                "elapsed_seconds": int(elapsed),
                            },
                        })
                    except Exception:
                        break

                    # If timer hit zero, trigger loop fail from here too
                    if remaining <= 0:
                        # Cancel the sleep-based timer so it doesn't double-fire
                        timer_task = self._loop_timers.pop(session_id, None)
                        if timer_task and not timer_task.done():
                            timer_task.cancel()
                        scenario_name = state.scenario.value
                        death_messages = {
                            "last_train": "The train pulls into the station. The truth walks away. Time folds back.",
                            "locked_room": "The clock strikes twelve. The room seals itself again.",
                            "dinner_party": "The dessert is served. The poison takes hold. You were too late.",
                            "the_signal": "The signal reaches full power. Emergency lights pulse red. Again.",
                            "the_crash": "The federal team arrives. They take over the scene. The evidence goes cold.",
                            "the_heist": "The lockdown lifts. The thief walks free. The diamond stays hidden.",
                            "room_414": "The hotel lawyer arrives. The crime scene is sealed. Case closed — incorrectly.",
                            "the_factory": "The company lawyers descend. The falsified records replace the real ones.",
                        }
                        death_desc = death_messages.get(scenario_name, "Time ran out. The loop resets.")
                        await self._handle_loop_fail(session_id, death_desc)
                        break

        self._timer_update_tasks[session_id] = asyncio.create_task(_send_updates())

    async def _handle_loop_fail(self, session_id: str, death_description: str = ""):
        """Handle loop failure — record, notify client, prepare for restart."""
        state = self.game_states.get(session_id)
        ws = self.websockets.get(session_id)

        if not state or state.loop_status != LoopStatus.ACTIVE:
            return

        state.loop_status = LoopStatus.FAILED
        self._cancel_timers(session_id)

        # Calculate duration
        duration = 0.0
        if state.loop_start_time:
            duration = time.time() - state.loop_start_time

        # Find current loop entry or create one
        current_entry = None
        for entry in state.loop_history:
            if entry.loop_number == state.current_loop:
                current_entry = entry
                break

        if not current_entry:
            current_entry = LoopEntry(loop_number=state.current_loop)
            state.loop_history.append(current_entry)

        current_entry.status = LoopStatus.FAILED
        current_entry.duration_seconds = duration
        current_entry.death_description = death_description
        current_entry.clues_found = [c.id for c in state.clues if c.loop_discovered == state.current_loop]

        # Generate death image in background
        asyncio.create_task(
            self._generate_death_image(session_id, death_description)
        )

        # Disconnect Gemini Live
        live = self.live_sessions.pop(session_id, None)
        if live:
            await live.disconnect()

        # Notify client
        if ws:
            try:
                await ws.send_json({
                    "type": "loop_failed",
                    "data": {
                        "loop_number": state.current_loop,
                        "death_description": death_description,
                        "duration_seconds": round(duration),
                        "total_clues": len(state.clues),
                        "key_clues": sum(1 for c in state.clues if c.is_key_clue),
                    },
                })
            except Exception:
                pass

        # Prepare next loop
        state.current_loop += 1

        # Persist
        await self.db.save_session(
            session_id, state.scenario.value, state.to_dict()
        )

    async def _handle_loop_break(self, session_id: str):
        """Handle the player breaking the loop — they win!"""
        state = self.game_states.get(session_id)
        ws = self.websockets.get(session_id)

        if not state:
            return

        state.loop_status = LoopStatus.BROKEN
        state.is_complete = True
        self._cancel_timers(session_id)

        duration = 0.0
        if state.loop_start_time:
            duration = time.time() - state.loop_start_time

        # Record final loop
        current_entry = None
        for entry in state.loop_history:
            if entry.loop_number == state.current_loop:
                current_entry = entry
                break

        if not current_entry:
            current_entry = LoopEntry(loop_number=state.current_loop)
            state.loop_history.append(current_entry)

        current_entry.status = LoopStatus.BROKEN
        current_entry.duration_seconds = duration
        current_entry.summary = "The loop was broken. Mystery solved."

        # Generate victory image
        config = get_scenario_config(state.scenario)
        asyncio.create_task(
            self._generate_victory_image(session_id, config["name"])
        )

        # Notify client
        if ws:
            try:
                await ws.send_json({
                    "type": "loop_broken",
                    "data": {
                        "loop_number": state.current_loop,
                        "total_loops": state.current_loop,
                        "total_clues": len(state.clues),
                        "key_clues": sum(1 for c in state.clues if c.is_key_clue),
                        "duration_seconds": round(duration),
                        "scenario": state.scenario.value,
                    },
                })
            except Exception:
                pass

        # Disconnect Live
        live = self.live_sessions.pop(session_id, None)
        if live:
            await live.disconnect()

        # Persist
        await self.db.save_session(
            session_id, state.scenario.value, state.to_dict()
        )

    async def restart_loop(self, session_id: str, websocket: WebSocket):
        """Restart the loop (after failure). Creates a new LoopEntry and reconnects."""
        state = self.game_states.get(session_id)
        if not state:
            return

        # Reset loop status
        state.loop_status = LoopStatus.ACTIVE

        # Create a new loop entry
        new_entry = LoopEntry(loop_number=state.current_loop)
        state.loop_history.append(new_entry)

        # Disconnect old live session
        live = self.live_sessions.pop(session_id, None)
        if live:
            await live.disconnect()

        # Start the new loop
        await self.start_loop(session_id, websocket)

    async def handle_audio(self, session_id: str, audio_data: bytes):
        """Forward audio data to Gemini Live."""
        live = self.live_sessions.get(session_id)
        if live:
            await live.send_audio(audio_data)

    async def handle_text_input(self, session_id: str, text: str, websocket: WebSocket):
        """Handle text input from the user (chosen action)."""
        print(f"[SessionManager] User chose: {text[:80]}", flush=True)
        state = self.game_states.get(session_id)
        live = self.live_sessions.get(session_id)
        if live and state:
            # Build context-rich prompt so the choice truly shapes the story
            clue_count = len(state.clues)
            key_clues = sum(1 for c in state.clues if c.is_key_clue)
            loop = state.current_loop
            player_name = state.player_name

            await live.send_text(
                f"[PLAYER ACTION — LOOP {loop}]\n"
                f"The player ({player_name}) has decided to: {text}\n\n"
                f"REACT TO THIS CHOICE NATURALLY AND INTERACTIVELY:\n"
                f"- START by acknowledging what the player tried to do in a conversational way. "
                f"For example: 'You try to bribe the guard — bad idea. He shoves the money back and gets hostile.' "
                f"or 'You lean in and ask about the insurance. Diana's smile freezes.' "
                f"or 'Bold move. You grab the fire extinguisher — and that's when you notice the blood.'\n"
                f"- The world and characters REACT realistically. People can refuse, get angry, lie, cooperate, or be surprised. "
                f"Not every action succeeds. Bad ideas should backfire. Good ideas should reward the player.\n"
                f"- Show CONSEQUENCES — if they search something, describe what they find (or don't). "
                f"If they confront someone, show that person's real reaction (defensive, scared, angry, dismissive).\n"
                f"- Be dynamic and unpredictable. Characters have personalities — they don't just passively answer questions.\n\n"
                f"Context: {clue_count} clues found ({key_clues} key clues / {state.total_clues_needed} needed). "
                f"Mood: {state.current_mood.value}. "
                f"{'The player is close to solving the mystery — raise the stakes!' if key_clues >= state.total_clues_needed - 1 else ''}\n\n"
                f"IMPORTANT RULES:\n"
                f"- Speak 3-5 clear sentences. Keep each sentence punchy and direct.\n"
                f"- You MUST complete your final sentence. NEVER stop mid-word or mid-sentence.\n"
                f"- ALWAYS end with a question for the player.\n"
                f"- End with a short, varied question. Examples: 'What's your next move?', 'Where do you look next?', "
                f"'What do you make of this?', 'What now?'. "
                f"Only use the player's name '{player_name}' in the question occasionally — most turns should NOT include it. "
                f"NEVER repeat the same question format twice in a row.\n"
                f"- If you feel yourself running long, STOP and ask the question immediately."
            )

    def _cancel_timers(self, session_id: str):
        """Cancel all timers for a session."""
        timer = self._loop_timers.pop(session_id, None)
        if timer and not timer.done():
            timer.cancel()

        update_task = self._timer_update_tasks.pop(session_id, None)
        if update_task and not update_task.done():
            update_task.cancel()

    async def _generate_scene_image(self, session_id: str, state: GameState):
        """Generate and send a scene image for loop start."""
        config = get_scenario_config(state.scenario)
        try:
            url = await self.image_gen.generate_scene_image(
                state.scenario,
                config["opening_narration"][:200],
                state.current_loop,
            )
            if url:
                ws = self.websockets.get(session_id)
                if ws:
                    await ws.send_json({
                        "type": "scene_image",
                        "data": {"image_url": url, "loop_number": state.current_loop},
                    })
        except Exception as e:
            print(f"Scene image generation failed: {e}", flush=True)

    async def _update_scene_image(self, session_id: str, narration_text: str):
        """Generate a new scene image based on the latest narration."""
        state = self.game_states.get(session_id)
        if not state:
            return
        try:
            # Use the last ~200 chars of narration as the scene description
            scene_desc = narration_text[-200:] if len(narration_text) > 200 else narration_text
            url = await self.image_gen.generate_scene_image(
                state.scenario,
                scene_desc,
                state.current_loop,
            )
            if url:
                ws = self.websockets.get(session_id)
                if ws:
                    await ws.send_json({
                        "type": "scene_image",
                        "data": {"image_url": url},
                    })
        except Exception as e:
            print(f"Scene image update failed: {e}", flush=True)

    async def _generate_clue_image(self, session_id: str, clue: Clue):
        """Generate and send a clue illustration."""
        state = self.game_states.get(session_id)
        if not state:
            return
        try:
            url = await self.image_gen.generate_clue_image(
                state.scenario, clue.text, clue.detail
            )
            if url:
                clue.image_url = url
                ws = self.websockets.get(session_id)
                if ws:
                    await ws.send_json({
                        "type": "clue_image",
                        "data": {"clue_id": clue.id, "image_url": url},
                    })
        except Exception as e:
            print(f"Clue image generation failed: {e}", flush=True)

    async def _generate_death_image(self, session_id: str, death_description: str):
        """Generate and send a death scene image."""
        state = self.game_states.get(session_id)
        if not state:
            return
        try:
            url = await self.image_gen.generate_death_image(
                state.scenario, death_description, state.current_loop - 1
            )
            if url:
                # Update the loop entry
                for entry in state.loop_history:
                    if entry.loop_number == state.current_loop - 1:
                        entry.death_image_url = url
                        break

                ws = self.websockets.get(session_id)
                if ws:
                    await ws.send_json({
                        "type": "death_image",
                        "data": {"image_url": url, "loop_number": state.current_loop - 1},
                    })
        except Exception as e:
            print(f"Death image generation failed: {e}", flush=True)

    async def _generate_victory_image(self, session_id: str, scenario_name: str):
        """Generate and send a victory image."""
        state = self.game_states.get(session_id)
        if not state:
            return
        try:
            url = await self.image_gen.generate_victory_image(
                state.scenario,
                f"The mystery of {scenario_name} is solved. The time loop is broken. Dawn breaks.",
            )
            if url:
                ws = self.websockets.get(session_id)
                if ws:
                    await ws.send_json({
                        "type": "victory_image",
                        "data": {"image_url": url},
                    })
        except Exception as e:
            print(f"Victory image generation failed: {e}", flush=True)

    async def _generate_choices(self, session_id: str, narrator_text: str):
        """Generate 3-4 contextual choices for the player based on the narrator's last turn."""
        state = self.game_states.get(session_id)
        ws = self.websockets.get(session_id)
        if not state or not ws:
            return

        if not narrator_text or len(narrator_text) < 20:
            return

        config = get_scenario_config(state.scenario)
        clue_count = len(state.clues)
        key_clues = sum(1 for c in state.clues if c.is_key_clue)

        # Build clue context
        found_clue_texts = [c.text for c in state.clues[-5:]]
        clue_context = f"Clues already found: {', '.join(found_clue_texts)}" if found_clue_texts else "No clues found yet."

        prompt = f"""You are generating player choices for an interactive time-loop mystery game.

SCENARIO: {config['name']}
CURRENT LOOP: {state.current_loop}
CLUES FOUND: {clue_count} (key: {key_clues}/{state.total_clues_needed})
MOOD: {state.current_mood.value}
{clue_context}

NARRATOR JUST SAID:
\"\"\"{narrator_text[-600:]}\"\"\"

Generate exactly 4 DISTINCT action choices that will lead to DIFFERENT story outcomes:
- Each choice must be 5-15 words, a concrete physical action
- Choice 1: INVESTIGATE — examine, search, or inspect something specific mentioned in the narration
- Choice 2: INTERACT — approach, confront, or speak to a specific character or entity
- Choice 3: BOLD/RISKY — a daring or dangerous action that could reveal secrets or cause trouble
- Choice 4: CAREFUL/CREATIVE — an unexpected, clever, or cautious approach

Each choice MUST reference specific details from what the narrator just said (names, objects, locations).
Do NOT use generic actions like "look around" or "search for clues".
{f"The player has {key_clues}/{state.total_clues_needed} key clues — include an option that could lead to solving the mystery." if key_clues >= state.total_clues_needed - 2 else ""}

Respond as a JSON array of 4 strings. Nothing else.
Example: ["Pry open the jammed airlock panel", "Confront Dr. Vasquez about the blood on her sleeve", "Smash the emergency beacon", "Quietly pocket the strange crystal before anyone notices"]"""

        try:
            from google import genai
            from google.genai import types as gtypes
            client = genai.Client(api_key=self.api_key)
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config=gtypes.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=200,
                ),
            )

            text = response.text.strip()
            # Parse JSON array
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            import json as _json
            choices = _json.loads(text)
            if isinstance(choices, list) and len(choices) >= 2:
                choices = [str(c) for c in choices[:4]]
                await ws.send_json({
                    "type": "choices",
                    "data": {"choices": choices},
                })
                print(f"[SessionManager] Sent {len(choices)} choices", flush=True)
            else:
                raise ValueError("Invalid choices format")

        except Exception as e:
            print(f"[SessionManager] Choice generation failed: {e}, using defaults", flush=True)
            # Fallback choices based on scenario
            fallback = self._get_fallback_choices(state)
            try:
                await ws.send_json({
                    "type": "choices",
                    "data": {"choices": fallback},
                })
            except Exception:
                pass

    @staticmethod
    def _get_fallback_choices(state: GameState) -> list[str]:
        """Generate generic fallback choices based on scenario."""
        scenario_choices = {
            Scenario.LAST_TRAIN: [
                "Search the luggage compartment",
                "Talk to the nervous passenger",
                "Examine the emergency brake",
                "Look out the window carefully",
            ],
            Scenario.LOCKED_ROOM: [
                "Examine the walls for hidden panels",
                "Talk to the other captives",
                "Study the clock mechanism",
                "Search under the furniture",
            ],
            Scenario.DINNER_PARTY: [
                "Watch the host closely",
                "Inspect the kitchen",
                "Strike up a conversation",
                "Examine the wine glasses",
            ],
            Scenario.THE_SIGNAL: [
                "Check the communications array",
                "Talk to the crew members",
                "Investigate the source of the signal",
                "Review the station logs",
            ],
        }
        from models.schemas import Scenario as Sc
        extra = {
            Sc.THE_CRASH: [
                "Examine the wreckage for tampering",
                "Question Diana about the insurance policy",
                "Check Ryan's phone for messages",
                "Ask Sergeant Vega about the head wound",
            ],
            Sc.THE_HEIST: [
                "Review the security camera footage",
                "Interview the museum director",
                "Examine the display case for prints",
                "Search the fire suppression system",
            ],
            Sc.ROOM_414: [
                "Check the hotel key card logs",
                "Interview the guest in Room 415",
                "Examine the victim's laptop",
                "Question the assistant's alibi",
            ],
            Sc.THE_FACTORY: [
                "Inspect the disabled safety systems",
                "Review the maintenance logs",
                "Talk to the surviving coworker",
                "Check the safety inspector's reports",
            ],
        }
        return {**scenario_choices, **extra}.get(state.scenario, [
            "Look around carefully",
            "Talk to someone nearby",
            "Search for clues",
            "Wait and observe",
        ])

    @staticmethod
    def _clean_transcript(text: str) -> str:
        """Clean Gemini's transcript by removing internal thinking/reasoning."""
        if not text:
            return text

        # Remove lines that look like thinking/reasoning (bold headers)
        lines = text.split('\n')
        cleaned_lines = []
        skip_thinking = True

        for line in lines:
            stripped = line.strip()

            if not stripped and skip_thinking:
                continue

            # Skip bold markdown headers (thinking markers)
            if stripped.startswith('**') and stripped.endswith('**'):
                continue

            # Skip lines that look like internal reasoning
            if skip_thinking and any(
                stripped.lower().startswith(prefix)
                for prefix in [
                    "i'm ", "i am ", "let me ", "i'll ", "i need to ",
                    "i should ", "i want to ", "i've ", "i have ",
                    "okay,", "ok,", "alright,", "so,",
                    "now ", "here ", "thinking", "planning",
                    "the narration", "my goal", "my aim",
                    "crafting", "focusing", "finalized",
                    "incorporating", "considering", "building",
                ]
            ):
                continue

            skip_thinking = False
            cleaned_lines.append(line)

        result = '\n'.join(cleaned_lines).strip()

        if not result:
            result = re.sub(r'\*\*[^*]+\*\*\s*', '', text).strip()

        return result if result else text

    async def disconnect(self, session_id: str):
        """Clean up a disconnected session."""
        self._cancel_timers(session_id)

        live = self.live_sessions.pop(session_id, None)
        if live:
            await live.disconnect()

        self.clue_detectors.pop(session_id, None)
        self.websockets.pop(session_id, None)

    async def get_game_state(self, session_id: str) -> Optional[GameState]:
        """Get current game state without creating."""
        return self.game_states.get(session_id)
