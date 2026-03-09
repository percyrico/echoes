# Echoes — AI-Powered Interactive Mystery Storytelling

**"Every loop reveals the truth."**

---

## Inspiration

We wanted to explore a question: *what happens when you give an AI narrator full creative control over a live, spoken mystery — and let the listener shape the story in real time?*

Interactive fiction has always been text on a screen. Audiobooks are passive. We saw a gap: a storytelling experience where the narrator *speaks to you* live, reacts to your decisions, and adapts the narrative in real time. Not pre-recorded. Not scripted. A living story.

The time-loop structure — inspired by narratives like Outer Wilds and 12 Minutes — gave us the perfect framework. Each loop is a self-contained chapter. Failure isn't punishment, it's progress. Every reset carries forward what you've learned, building toward a resolution that feels earned.

The Gemini Live API made this possible. With native audio generation and real-time streaming, we could build a narrator that doesn't read a script but *performs* one — adjusting tone, pacing, and content based on what the listener does. Google ADK gave us the multi-agent architecture to coordinate narration, analysis, visuals, and sound simultaneously. That combination was the spark.

## What it does

Echoes is an interactive mystery storytelling platform powered by real-time AI voice narration and a multi-agent backend built with **Google ADK**.

You step into the role of a detective investigating one of **8 original mystery scenarios**. A Gemini-powered narrator tells you the story out loud — in real time, with natural voice inflection and dramatic pacing. You make choices that shape the narrative. The narrator responds dynamically: pursue a dead end and the story acknowledges it; follow the right lead and new paths open up.

Each session runs on a **5-minute loop**. When time expires, the story resets — but every clue you've uncovered persists across resets. Over multiple loops, you piece together the full picture. Once you've gathered enough critical evidence, you can break the loop and reach the story's resolution.

### The Scenarios

Echoes includes **8 fully authored mystery scenarios**, each with unique characters, interconnected clue networks, red herrings, and narrative arcs:

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

### The Experience

1. **Choose a scenario** and enter your name. The narrator addresses you personally throughout the story.
2. **Listen** as the narrator sets the scene — not text-to-speech, but Gemini's native audio generation with natural pacing, tone shifts, and dramatic emphasis.
3. **Make decisions** from context-aware options that appear at story beats. The narrator incorporates your choices into the narrative. Choose to confront a suspect? The narrator describes the tension. Try to force a locked door? The narrator tells you it won't budge — and maybe someone heard you.
4. **Discover clues** that are automatically extracted from the narrator's spoken words using real-time NLP analysis. Key evidence is highlighted and persists across loop resets.
5. **Experience the atmosphere.** AI-generated scene illustrations shift as the story progresses. A dynamic mood system drives ambient soundscapes from a curated library of 27 tracks. Visual particle effects respond to the story's emotional tone.
6. **Reach the resolution** once enough evidence has been gathered. The loop breaks and the mystery concludes.

## How we built it

### Architecture — ADK Multi-Agent Orchestration

The core of Echoes is a **multi-agent system built on Google ADK** (Agent Development Kit). Each aspect of the storytelling experience is handled by a specialized agent, coordinated by a central orchestrator:

```
Browser (React + Vite + Tailwind + Framer Motion)
    |
    WebSocket
    |
FastAPI Backend (Cloud Run)
    |
    +-- SessionManager (ADK Orchestrator Agent)
    |       Coordinates all sub-agents per session.
    |       Manages narrative state, loop lifecycle, and
    |       real-time event routing between agents.
    |
    +-- NarratorAgent (Gemini Live — gemini-2.5-flash-native-audio)
    |       Real-time voice narration via Gemini Live API.
    |       Streams native audio + transcript. Handles
    |       auto-continuation when model hits turn limits.
    |
    +-- ClueDetectorAgent (Gemini — gemini-2.5-flash-lite)
    |       Analyzes narrator transcript in real time.
    |       Detects story-critical evidence, mood shifts,
    |       and resolution conditions against scenario definitions.
    |
    +-- IllustratorAgent (Gemini — gemini-2.0-flash-exp-image-generation)
    |       Generates scene illustrations triggered early in narration
    |       (after 80 chars of transcript). Produces clue images,
    |       transition scenes, and resolution illustrations.
    |
    +-- ComposerAgent (Rule-based + ADK tool)
            Maps narrative mood to ambient audio cues from
            a curated CC0 soundscape library. Controls crossfade
            parameters per scenario and emotional state.
```

### How the Agents Collaborate

Every narrative turn follows this agent pipeline:

1. **SessionManager** receives the listener's choice and routes it to the NarratorAgent with full narrative context.
2. **NarratorAgent** (Gemini Live) generates spoken narration streamed as audio chunks + transcript text. The voice adapts to the scenario's tone — noir mysteries sound different from industrial investigations.
3. As transcript streams in, **ClueDetectorAgent** analyzes chunks incrementally — it doesn't wait for the full turn. When evidence is detected, the SessionManager immediately notifies the frontend and dispatches the **IllustratorAgent** to generate a clue illustration.
4. After ~80 characters of transcript, the **IllustratorAgent** generates a new scene illustration in parallel with ongoing narration — so the visual often arrives before the narrator finishes speaking.
5. On mood changes detected by the ClueDetectorAgent, the **ComposerAgent** selects new ambient audio and sends audio cue events to the frontend for seamless crossfading.
6. On turn completion, the SessionManager checks for auto-continuation (was the narrator cut off mid-sentence?), generates contextual choices, and updates narrative state in SQLite.

This agent-per-concern architecture means each agent can be independently tested, tuned, or replaced. The ClueDetectorAgent uses `gemini-2.5-flash-lite` for speed, while the NarratorAgent uses `gemini-2.5-flash-native-audio-latest` for voice quality — different models optimized for different responsibilities.

### Backend — Python + FastAPI + Google ADK

- **Google ADK** provides the agent framework: each storytelling service (narration, clue detection, illustration, audio composition) is structured as an ADK-compatible agent with defined inputs, outputs, and tool functions. The SessionManager acts as the orchestrator, dispatching work to sub-agents and assembling their outputs into a cohesive narrative turn.
- **Gemini Live API** (`gemini-2.5-flash-native-audio-latest`) streams native audio narration. The backend manages scenario context, listener choices, and loop history, forwarding audio chunks and transcript text to the frontend in real time.
- **Gemini image generation** (`gemini-2.0-flash-exp-image-generation`) produces scene illustrations triggered early in each narrative turn to minimize perceived latency.
- **Real-time NLP analysis** via `gemini-2.5-flash-lite` processes narrator transcript incrementally to detect when critical story evidence is revealed.
- **SQLite + aiosqlite** stores sessions, discovered clues, and loop history with zero external database dependencies.
- **Auto-continuation engine** detects when the voice model hits its turn length limit and automatically prompts the model to continue — the listener hears seamless narration with no gaps or awkward stops.

### Frontend — React + TypeScript

- **Web Audio API** schedules audio chunk playback with sample-level precision for gapless narration. No clicks, no pauses between chunks.
- **Framer Motion** drives UI animations, scene illustration crossfades (with preloading), and mood-responsive particle effects.
- **Zustand** manages application state: scenario, loop progress, discovered clues, mood, timer, and narrator status.
- **Responsive layout** with mobile-optimized controls — choices are pinned to the bottom of the viewport so they're always accessible.

### Infrastructure

- **Docker** multi-stage build: Node 20 compiles the React frontend, Python 3.11-slim serves both the API and the static SPA from a single container.
- **Google Cloud Run** for serverless deployment with `min-instances: 0` (scales to zero when idle for minimal cost) and `max-instances: 1`.
- Zero external service dependencies beyond the Gemini API — the entire platform runs with SQLite on a single instance.

## Challenges we ran into

**Gemini Live audio turn limits.** The voice model has a maximum output length per turn. Mid-sentence cutoffs break immersion. We solved this by monitoring the transcript stream — if a turn ends without terminal punctuation, the SessionManager automatically sends a continuation prompt. The listener never notices. The narrator continues seamlessly.

**Coordinating multiple agents in real time.** The ClueDetectorAgent, IllustratorAgent, and ComposerAgent all need to react to the NarratorAgent's output simultaneously. Sequential processing would add unacceptable latency. Using ADK's agent architecture, the SessionManager dispatches these agents as concurrent async tasks — clue detection, illustration, and mood analysis all happen in parallel while the narrator is still speaking.

**Incremental evidence detection.** Waiting for the narrator to finish before analyzing for clues added seconds of delay. The ClueDetectorAgent processes transcript chunks every 150 characters at sentence boundaries — clues are surfaced while the narrator is still revealing them.

**Gapless audio playback.** Streaming audio chunks over WebSocket and playing them with `<audio>` elements produces audible gaps. We switched to the Web Audio API, decoding each chunk into an AudioBuffer and scheduling playback at exact sample-level timestamps. The result sounds like a single continuous audio stream.

**Illustration latency.** Waiting for a full narrative turn before generating a scene illustration added noticeable delay. The IllustratorAgent now triggers after just 80 characters of transcript — enough context for a relevant image, fast enough that it often arrives before the narrator finishes speaking.

## Accomplishments that we're proud of

- **Multi-agent architecture that works in real time.** Four specialized agents run concurrently within a single narrative turn, each using the right Gemini model for its task. ADK made this modular and maintainable.
- **Seamless voice narration** that feels like a human storyteller. The auto-continuation system ensures the narrator never stops mid-sentence or loses its thread.
- **8 complete mystery scenarios** with interconnected clue systems, red herrings, and satisfying resolutions. Each one unfolds differently across multiple loops.
- **The time-loop structure works narratively.** Evidence persistence means early loops feel like exploration and later loops feel like the pieces coming together. The 5-minute constraint creates genuine tension and forces meaningful choices.
- **Zero external dependencies** beyond the Gemini API. No Redis, no Postgres, no message queue. SQLite and in-memory state handle everything. Clone, build, experience.
- **Mood-reactive atmosphere.** The ComposerAgent shifts ambient audio naturally with the narrative. A tense interrogation sounds and feels different from a quiet evidence review.

## What we learned

- **Multi-agent design simplifies complex AI applications.** Decomposing the experience into NarratorAgent, ClueDetectorAgent, IllustratorAgent, and ComposerAgent — each with a single responsibility and an optimized model — made the system dramatically easier to reason about. ADK provided the structure to make this decomposition natural.
- **Native audio generation is a different paradigm.** It's not TTS. The model controls pacing, emphasis, and emotional tone. Designing prompts for *spoken* output requires thinking about rhythm and delivery, not just content.
- **Time constraints transform AI interactions.** Without the 5-minute loop, listeners would exhaustively explore every option. The constraint forces intuition and risk-taking — exactly what a mystery narrative should feel like.
- **Early triggering beats post-processing.** Whether it's the IllustratorAgent generating images or the ClueDetectorAgent analyzing transcript, starting work before you have complete data produces a dramatically more responsive experience.
- **Agent-per-model is a powerful pattern.** Using `gemini-2.5-flash-native-audio` for narration, `gemini-2.5-flash-lite` for analysis, and `gemini-2.0-flash-exp-image-generation` for illustrations — each agent picks the model optimized for its job.

## What's next

- **Voice input** — let the listener speak directly to the narrator via microphone, using Gemini Live's bidirectional audio for fully conversational storytelling.
- **Collaborative sessions** — multiple listeners join the same mystery, each making independent choices that affect the shared narrative.
- **Expanded scenario library** — more mysteries with mid-story branch points where different evidence combinations unlock entirely different narrative threads.
- **ADK tool functions** — expose narrative actions (examine evidence, interrogate character, move to location) as ADK tool functions that the NarratorAgent can invoke directly, enabling tighter integration between narration and story mechanics.

## Try it out

**Live Demo:** https://echoes-cxotjai2ta-uc.a.run.app

```bash
git clone https://github.com/percyrico/echoes.git
cd echoes
cp .env.example .env   # add your GOOGLE_API_KEY
docker-compose up
```

Open `http://localhost:3000`. Choose a mystery. Listen closely. You have 5 minutes.

## Built with

Python, FastAPI, Google ADK, Google Gemini Live API (`gemini-2.5-flash-native-audio`), Gemini Flash (`gemini-2.5-flash-lite`), Gemini Image Generation (`gemini-2.0-flash-exp`), React, TypeScript, Tailwind CSS, Framer Motion, Zustand, WebSockets, Web Audio API, SQLite, aiosqlite, Docker, Google Cloud Run
