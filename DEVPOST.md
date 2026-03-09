# Echoes — Time-Loop Mystery Game

**"Every loop reveals the truth."**

---

## Inspiration

We wanted to answer a simple question: *what if a detective game could talk back to you?*

Time-loop narratives — Groundhog Day, Outer Wilds, 12 Minutes — are compelling because they turn failure into progress. Every reset teaches you something. We realized that pairing a time-loop mechanic with a live AI narrator could create something genuinely new: a mystery game where the story is never read, it is *spoken to you* in real time, and the narrator actually reacts to your decisions. Make a bad call and the narrator will let you know — sometimes with consequences that end your loop early.

The Gemini Live API made this possible. With native audio generation, we could build a narrator that does not just read a script but performs one, adjusting tone, pacing, and content based on what the player does. Google ADK gave us the framework to orchestrate multiple specialized agents — each responsible for a different aspect of the game — into a cohesive, real-time experience. That was the spark.

## What it does

Echoes is an interactive time-loop mystery game powered by real-time AI voice narration and a multi-agent backend built with **Google ADK**.

A Gemini-powered narrator tells you a detective story — out loud, in real time. You are the detective. You have **5 minutes per loop** to explore the scene, interrogate suspects, examine evidence, and piece together what happened. When time runs out, the loop resets. But your clues carry over.

Across multiple loops, you accumulate key evidence. Once you have gathered enough critical clues, you can **break the loop** and solve the mystery.

### The Scenarios

Echoes ships with **8 fully authored scenarios**, each with unique characters, clue networks, red herrings, and win conditions:

**Classic Mysteries**
- **The Last Train** — A passenger is found dead on a night train. The conductor locked the doors. Everyone has an alibi. Everyone is lying.
- **The Locked Room** — A professor is killed inside a study locked from the inside. No weapon found. The window was painted shut years ago.
- **The Dinner Party** — A host collapses mid-toast at a dinner for six. The wine was shared. The motive was not.
- **The Signal** — A coastal lighthouse keeper vanishes. The light was left on. The logbook entry for that night was torn out.

**Detective Investigations**
- **The Crash** — A single-car accident on a straight road. No skid marks. The victim's phone was wiped remotely 30 seconds after impact.
- **The Heist** — A museum robbery with no alarms triggered. The thief left one painting behind — the most valuable one.
- **Room 414** — A hotel guest checks out but never leaves the building. Housekeeping finds the room spotless. Too spotless.
- **The Factory** — A worker dies in an industrial accident. Safety records were falsified. The question is by whom and why.

### How It Plays

1. **Pick a scenario** and enter your name. The narrator addresses you personally throughout.
2. **Listen** as the narrator sets the scene with full voice narration — not text-to-speech, but Gemini's native audio generation with natural pacing and inflection.
3. **Make choices** by selecting from context-aware options. The narrator reacts dynamically. Try to force open a locked door? The narrator will tell you it does not budge — and maybe someone heard you trying.
4. **Collect clues** that are automatically detected from the narrator's transcript by the ClueDetector agent using Gemini-powered NLP analysis.
5. **Watch the clock.** When 5 minutes expire, the loop resets with a scenario-specific "death" message. But your clues persist.
6. **Break the loop** once you have found enough key evidence. Accuse the right suspect with the right proof and the mystery ends.

The game generates **AI scene images** that update as the story progresses — when you move to a new location or discover something important, the IllustratorAgent generates a new visual that fades in seamlessly. A **dynamic mood system** tracks six emotional states (tense, eerie, dramatic, mysterious, calm, urgent), with the ComposerAgent selecting appropriate ambient audio from a library of 27 bundled soundscapes and triggering visual particle effects on screen.

## How we built it

### Architecture — ADK Multi-Agent Orchestration

The core of Echoes is a **multi-agent system built on Google ADK** (Agent Development Kit). Instead of a monolithic AI handler, the game uses specialized agents that each handle a distinct aspect of the experience, coordinated by a central orchestrator.

```
Browser (React + Vite + Tailwind + Framer Motion)
    │
    WebSocket
    │
FastAPI Backend (Cloud Run)
    │
    ├── SessionManager (ADK Orchestrator Agent)
    │       Coordinates all sub-agents per game session.
    │       Manages game state, loop lifecycle, and
    │       real-time event routing between agents.
    │
    ├── NarratorAgent (Gemini Live — gemini-2.5-flash-native-audio)
    │       Real-time voice narration via Gemini Live API.
    │       Streams native audio + transcript. Handles
    │       auto-continuation when model hits turn limits.
    │
    ├── ClueDetectorAgent (Gemini — gemini-2.5-flash-lite)
    │       Analyzes narrator transcript in real time.
    │       Detects clue discoveries, mood shifts, and
    │       win conditions against scenario clue definitions.
    │
    ├── IllustratorAgent (Gemini — gemini-2.0-flash-exp-image-generation)
    │       Generates scene images triggered early in narration
    │       (after 80 chars of transcript). Produces clue images,
    │       death scenes, and victory illustrations.
    │
    └── ComposerAgent (Rule-based + ADK tool)
            Maps scene mood → ambient audio cues from
            a bundled CC0 soundscape library. Selects tracks
            and controls crossfade parameters per scenario.
```

### How the Agents Work Together

Every game turn follows this agent pipeline:

1. **SessionManager** receives player input (text choice or audio) and routes it to the NarratorAgent.
2. **NarratorAgent** (Gemini Live) generates spoken narration streamed as audio chunks + transcript text.
3. As transcript streams in, **ClueDetectorAgent** analyzes chunks incrementally — it does not wait for the full turn. When a clue is detected, the SessionManager immediately notifies the frontend and dispatches the **IllustratorAgent** to generate a clue image.
4. After ~80 characters of transcript, the **IllustratorAgent** is triggered to generate a new scene image in parallel with ongoing narration — so the image often arrives before the narrator finishes speaking.
5. On mood changes detected by the ClueDetectorAgent, the **ComposerAgent** selects new ambient audio and sends audio cue events to the frontend.
6. On turn completion, the SessionManager checks for auto-continuation (was the narrator cut off mid-sentence?), generates player choices, and updates game state in SQLite.

This agent-per-concern architecture means each agent can be independently tested, swapped, or enhanced. The ClueDetectorAgent uses `gemini-2.5-flash-lite` for speed, while the NarratorAgent uses `gemini-2.5-flash-native-audio-latest` for voice quality — different models optimized for different jobs.

### Backend — Python + FastAPI + Google ADK

- **Google ADK** provides the agent framework: each game service (narration, clue detection, image generation, audio composition) is structured as an ADK-compatible agent with defined inputs, outputs, and tool functions. The SessionManager acts as the orchestrator agent, dispatching work to sub-agents and aggregating their results into a coherent game turn.
- **Gemini Live API integration** (`gemini-2.5-flash-native-audio-latest`) streams native audio narration over WebSocket. The backend sends scenario context and player choices to Gemini, receives audio chunks and transcript text, and forwards both to the frontend.
- **Gemini image generation** (`gemini-2.0-flash-exp-image-generation`) produces scene images triggered early in each narrator turn to minimize perceived latency.
- **NLP clue extraction** via `gemini-2.5-flash-lite` analyzes narrator transcript in real time to detect when key evidence is mentioned, automatically adding discovered clues to the player's inventory.
- **SQLite + aiosqlite** stores game sessions, discovered clues, and loop history with zero external database dependencies.
- **Auto-continuation engine** detects when the voice model hits its turn length limit (transcript ends without terminal punctuation) and automatically prompts the model to continue — the player hears seamless narration with no gaps.

### Frontend — React + TypeScript

- **Web Audio API** schedules audio chunk playback with precise timing for gapless narrator audio. No clicks, no pauses between chunks.
- **Framer Motion** drives UI animations, scene image crossfades (with preloading), and particle effects tied to the mood system.
- **Zustand** manages global game state: current scenario, loop count, discovered clues, mood, timer, and narrator status.
- **Module-level WebSocket singleton** ensures a single connection is shared cleanly across all React components without prop drilling or context issues.
- **Cache-busting** on generated images prevents browsers from serving stale scene art after image regeneration.

### Infrastructure

- **Docker** multi-stage build: Node 20 compiles the React frontend, Python 3.11-slim serves both the API and the static SPA from a single container.
- **Google Cloud Run** for serverless deployment with `min-instances: 0` (scales to zero when idle for minimal cost) and `max-instances: 1`.
- Zero external service dependencies beyond the Gemini API — the entire game runs with SQLite on a single machine.

## Challenges we ran into

**Gemini Live audio turn limits.** The voice model has a maximum output length per turn. Mid-sentence cutoffs destroy immersion. We solved this by monitoring the transcript stream — if a turn ends without terminal punctuation (period, question mark, exclamation point), the SessionManager agent automatically sends a continuation prompt. The player never notices. The narrator just keeps talking.

**Coordinating multiple agents in real time.** The ClueDetectorAgent, IllustratorAgent, and ComposerAgent all need to react to the NarratorAgent's output simultaneously. Processing them sequentially would add unacceptable latency. Using ADK's agent architecture, the SessionManager dispatches these agents as concurrent async tasks — clue detection, image generation, and mood analysis all happen in parallel while the narrator is still speaking. Google ADK's structured approach to agent inputs/outputs made this clean to implement.

**Incremental clue detection.** Waiting for the narrator to finish before analyzing for clues added seconds of delay. We built the ClueDetectorAgent to process transcript chunks incrementally — every 150 characters at sentence boundaries. This means clues are discovered and shown to the player while the narrator is still talking about them.

**Gapless audio playback.** Streaming audio chunks from a WebSocket and playing them back with `<audio>` elements produces audible gaps. We switched to the Web Audio API, decoding each chunk into an AudioBuffer and scheduling playback at exact sample-level timestamps. The result is seamless narration that sounds like a single continuous stream.

**Image generation latency.** Waiting for the narrator to finish a full turn before generating a scene image added noticeable delay. The IllustratorAgent now triggers after just 80 characters of transcript — enough context to produce a relevant image, fast enough that the image often arrives before the narrator finishes speaking.

**Stale cached images.** Browsers aggressively cache images by URL. When the IllustratorAgent generates a new scene image at the same endpoint, players would see the old one. We append a timestamp query parameter to every image URL, forcing a fresh fetch every time.

## Accomplishments that we're proud of

- **Multi-agent architecture that works in real time.** Four specialized agents — narration, clue detection, illustration, and audio composition — run concurrently within a single game turn, each using the right Gemini model for its task. ADK made this modular and clean.
- **Seamless voice narration** that genuinely feels like a human game master telling you a story. The auto-continuation system means the narrator never awkwardly stops mid-sentence.
- **8 complete mystery scenarios** with interconnected clue systems, red herrings, and satisfying solutions. Each one plays differently across multiple loops.
- **The loop mechanic actually works narratively.** Clue persistence across resets means early loops feel like reconnaissance and later loops feel like a tightening net. The 5-minute pressure creates real tension.
- **Zero external dependencies** beyond the Gemini API. No Redis, no Postgres, no message queue. SQLite and in-memory state handle everything. Clone, build, play.
- **Mood-reactive atmosphere.** The ComposerAgent shifts ambient audio and particle effects naturally with the story. A tense interrogation scene sounds and looks different from a calm evidence review.

## What we learned

- **Multi-agent design simplifies complex AI applications.** What started as a monolithic game loop became much clearer when decomposed into NarratorAgent, ClueDetectorAgent, IllustratorAgent, and ComposerAgent. Each agent has a single responsibility and uses the Gemini model best suited for its task. ADK provided the structure to make this decomposition natural.
- **Native audio generation is a different paradigm.** It is not TTS. The model controls pacing, emphasis, and tone. Designing prompts for *spoken* output requires thinking about rhythm and breath, not just content.
- **Time pressure transforms AI interactions.** Without the 5-minute loop timer, players would exhaustively explore every option. The constraint forces intuition and risk-taking — exactly what detective work should feel like.
- **Early triggering beats post-processing.** Whether it is the IllustratorAgent generating images or the ClueDetectorAgent analyzing transcript, starting the work before you have complete data (and refining later) produces a dramatically more responsive experience.
- **Agent-per-model is a powerful pattern.** Using `gemini-2.5-flash-native-audio` for narration, `gemini-2.5-flash-lite` for clue detection, and `gemini-2.0-flash-exp-image-generation` for illustrations — each agent picks the model optimized for its job. ADK's framework made switching between models per agent straightforward.

## What's next

- **Voice input** — let the player speak to the narrator directly via microphone, using Gemini Live's bidirectional audio capabilities for fully conversational gameplay.
- **Collaborative multiplayer** — multiple players join the same mystery, each seeing the same narrator but making independent choices that affect the shared investigation.
- **More scenarios and branching paths** — expand the scenario library and add mid-story branch points where different clue combinations unlock entirely different narrative threads.
- **ADK tool functions** — expose game actions (examine evidence, interrogate suspect, move to location) as ADK tool functions that the NarratorAgent can invoke directly, enabling tighter integration between narration and game mechanics.

## Try it out

**Live Demo:** https://echoes-cxotjai2ta-uc.a.run.app

```bash
git clone <repo-url>
cd echoes
docker-compose up
```

Set your `GOOGLE_API_KEY` environment variable and open `http://localhost:5173`. Pick a mystery. Listen closely. You have 5 minutes.

## Built with

Python, FastAPI, Google ADK, Google Gemini Live API (`gemini-2.5-flash-native-audio`), Gemini Flash (`gemini-2.5-flash-lite`), Gemini Image Generation (`gemini-2.0-flash-exp`), React, TypeScript, Tailwind CSS, Framer Motion, Zustand, WebSockets, Web Audio API, SQLite, aiosqlite, Docker, Google Cloud Run
