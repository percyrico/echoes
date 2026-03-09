# Echoes — A Live AI Storyteller That Speaks Your Mystery

**"Every loop reveals the truth."**

---

## Inspiration

We love stories — but we wanted one that talks back.

Audiobooks are passive. Interactive fiction is silent text on a screen. We imagined something in between: an **AI storyteller** that speaks to you live, listens to your choices, and weaves the narrative around you in real time. Not pre-recorded. Not scripted. A narrator that *performs* — with voice, pacing, dramatic pauses, and the creative freedom to improvise.

We chose the mystery genre because mysteries demand participation. You can't just listen — you have to think, question, and decide. And we chose a time-loop structure because it turns the storyteller into a collaborator: each retelling refines the story based on what you've already uncovered.

The Gemini Live API gave us a narrator with a real voice. Google ADK gave us the multi-agent backbone to orchestrate narration, scene illustration, evidence tracking, and soundscapes — all running simultaneously, all in service of the story. That's how Echoes was born: an AI storyteller that performs a mystery just for you.

## What it does

Echoes is a **live AI storyteller** that narrates original mystery stories in real time using voice, illustrations, and ambient sound — shaped by your choices as you listen.

You pick one of **8 original mystery stories**. The AI narrator begins telling you the story out loud — setting scenes, voicing characters, building tension. At key moments, you make choices that steer the narrative. The narrator adapts: follow a promising lead and the story opens up; make a reckless move and you'll face the consequences.

Each telling runs on a **5-minute loop**. When time runs out, the story resets to the beginning — but every piece of evidence you've uncovered carries forward. Across multiple tellings, you accumulate the clues needed to unravel the full mystery. Once you've gathered enough, you can break the loop and reach the story's true ending.

Think of it as a storyteller sitting across from you, telling you a mystery — except this storyteller remembers every version of the story you've heard, adapts to your instincts, and illustrates the scenes as they narrate.

### The Stories

Echoes ships with **8 fully crafted mystery stories**, each with its own cast of characters, web of clues, red herrings, and a resolution that rewards careful listening:

**Classic Mysteries**
- **The Last Train** — A passenger found dead on a night train. The conductor locked the doors. Everyone has an alibi. Everyone is lying.
- **The Locked Room** — A professor killed inside a study locked from the inside. No weapon. The window was painted shut years ago.
- **The Dinner Party** — A host collapses mid-toast at a dinner for six. The wine was shared. The motive was not.
- **The Signal** — A lighthouse keeper vanishes. The light was left on. The logbook entry for that night was torn out.

**Investigations**
- **The Crash** — A single-car accident on a straight road. No skid marks. The victim's phone was wiped remotely 30 seconds after impact.
- **The Heist** — A museum robbery with no alarms triggered. The thief left one painting behind — the most valuable one.
- **Room 414** — A hotel guest checks out but never leaves the building. Housekeeping finds the room spotless. Too spotless.
- **The Factory** — A worker dies in an industrial accident. Safety records were falsified. The question is by whom — and why.

### How It Works

1. **Pick a story** and tell the narrator your name. The storyteller addresses you personally as the story unfolds.
2. **Listen** as the narrator performs the opening scene — this is Gemini's native audio generation, not text-to-speech. The voice has natural rhythm, emphasis, and emotional tone.
3. **Guide the story** by choosing from options that appear at narrative turning points. The storyteller weaves your decisions into the tale. Ask the wrong question and a character shuts down. Press the right lead and a secret unravels.
4. **Uncover clues** embedded in the narrator's words. The system detects evidence in real time and surfaces it visually — key clues persist across every retelling.
5. **Feel the atmosphere.** AI-generated illustrations shift as scenes change. Ambient soundscapes from a library of 27 curated tracks fade in and out with the story's mood. Visual effects pulse with the narrative tension.
6. **Solve the mystery** once you've gathered enough evidence across multiple tellings. Break the loop and hear the story's true ending.

## How we built it

### Architecture — Multi-Agent Storytelling Engine with Google ADK

Echoes is powered by a **multi-agent system built on Google ADK** (Agent Development Kit). Each dimension of the storytelling experience — voice, analysis, visuals, sound — is handled by a dedicated agent, all orchestrated in real time:

```
Browser (React + Vite + Tailwind + Framer Motion)
    |
    WebSocket (real-time bidirectional)
    |
FastAPI Backend (Google Cloud Run)
    |
    +-- StoryDirector (ADK Orchestrator Agent)
    |       Coordinates all storytelling agents per session.
    |       Manages narrative state, loop lifecycle, and
    |       real-time event routing between agents.
    |
    +-- NarratorAgent (Gemini Live — gemini-2.5-flash-native-audio)
    |       The voice of the story. Streams live narration
    |       via Gemini Live API with auto-continuation for
    |       seamless, uninterrupted storytelling.
    |
    +-- StoryAnalyst (Gemini — gemini-2.5-flash-lite)
    |       Listens to the narrator's own words in real time.
    |       Detects when clues are revealed, tracks mood shifts,
    |       and identifies when the story can reach resolution.
    |
    +-- IllustratorAgent (Gemini — gemini-2.0-flash-exp-image-generation)
    |       Paints the scenes as the narrator describes them.
    |       Generates illustrations mid-narration so visuals
    |       arrive while the storyteller is still speaking.
    |
    +-- ComposerAgent (Rule-based + ADK tool)
            Sets the mood with ambient soundscapes. Selects
            and crossfades tracks from a curated CC0 library
            based on the story's emotional state.
```

### How the Agents Tell a Story Together

Every narrative moment follows this pipeline:

1. **StoryDirector** receives the listener's choice and feeds it to the NarratorAgent with full story context — what's happened before, what clues have been found, what the listener knows.
2. **NarratorAgent** (Gemini Live) performs the next part of the story, streaming audio and transcript in real time. The voice adapts to tone — a noir mystery sounds different from an industrial thriller.
3. As the narrator speaks, the **StoryAnalyst** processes the transcript incrementally — not waiting for the narrator to finish. When a clue is woven into the narration, it's detected and surfaced immediately.
4. After just ~80 characters of narration, the **IllustratorAgent** begins generating a scene illustration in parallel — so the image often fades in while the narrator is still describing the scene.
5. When the StoryAnalyst detects a mood shift, the **ComposerAgent** crossfades to a new ambient track. Tension builds. Calm settles. The sound follows the story.
6. When the narrator finishes a passage, the StoryDirector checks for auto-continuation (did the narrator get cut off mid-sentence?), generates contextual story choices, and persists the narrative state.

Each agent uses the Gemini model best suited for its role: `gemini-2.5-flash-native-audio` for voice performance, `gemini-2.5-flash-lite` for fast transcript analysis, `gemini-2.0-flash-exp-image-generation` for scene illustration.

### Backend — Python + FastAPI + Google ADK

- **Google ADK** structures each storytelling service as an agent with defined inputs, outputs, and tools. The StoryDirector orchestrates them, dispatching work in parallel and assembling a cohesive multimodal story turn.
- **Gemini Live API** (`gemini-2.5-flash-native-audio-latest`) provides the narrator's voice — streamed live, with the model controlling pacing, inflection, and dramatic delivery.
- **Gemini image generation** creates scene illustrations triggered early in each narrative passage, before the narrator finishes speaking.
- **Real-time transcript analysis** via `gemini-2.5-flash-lite` processes the narrator's words incrementally to detect evidence, mood, and story-critical moments.
- **Auto-continuation** ensures the narrator never stops mid-sentence. If the voice model hits its turn limit, the system silently prompts it to continue. The listener hears one unbroken performance.
- **SQLite + aiosqlite** — zero external database dependencies. Story state, clues, and loop history all persist locally.

### Frontend — React + TypeScript

- **Web Audio API** with sample-level scheduling for gapless narrator audio. No pops, no gaps between chunks.
- **Framer Motion** for cinematic scene crossfades, mood-reactive particles, and smooth UI transitions.
- **Zustand** for lightweight state management across the storytelling interface.
- **Responsive design** — story choices are always visible on mobile, pinned to the bottom of the viewport.

### Infrastructure

- **Single Docker container** serves both the React frontend and FastAPI backend from one Cloud Run instance.
- **Google Cloud Run** with `min-instances: 0` — scales to zero when idle, minimal cost.
- No Redis, no Postgres, no message queues. Just SQLite and the Gemini API.

## Challenges we ran into

**The narrator would stop mid-sentence.** Gemini Live has a maximum output length per turn. A narrator cutting off mid-thought destroys the storytelling illusion. We built an auto-continuation system: the StoryDirector monitors the transcript and, if a turn ends without closing punctuation, silently prompts the narrator to continue. The listener hears one continuous performance.

**Four agents need to react to the narrator simultaneously.** The StoryAnalyst, IllustratorAgent, and ComposerAgent all consume the narrator's output — but processing them sequentially would make the story feel sluggish. ADK's agent architecture let us dispatch all three as concurrent tasks. Clue detection, illustration, and mood analysis happen in parallel while the narrator is still speaking.

**Clues hidden in narration are easy to miss.** The StoryAnalyst can't wait for the narrator to finish — that adds seconds of dead air. So it processes transcript chunks incrementally, every 150 characters at sentence boundaries. Clues surface while the narrator is still weaving them into the story.

**Streaming audio has gaps.** WebSocket audio chunks played through `<audio>` elements produce audible pops between segments. We moved to the Web Audio API, decoding each chunk into an AudioBuffer and scheduling playback at exact sample timestamps. The narrator now sounds like one continuous voice.

**Scene illustrations lag behind the story.** Generating an image after the narrator finishes speaking creates a noticeable pause. The IllustratorAgent now triggers after just 80 characters of transcript — enough context for a relevant scene, fast enough that the illustration often appears while the narrator is still describing it.

## Accomplishments that we're proud of

- **A storyteller that feels alive.** The narrator performs with natural voice, adapts to choices, and never awkwardly stops mid-sentence. It genuinely feels like someone is telling you a story.
- **Multi-agent storytelling in real time.** Four agents — narrator, analyst, illustrator, composer — collaborate on every story moment, each using the right Gemini model for its role. ADK made this clean and modular.
- **8 complete mystery stories** with layered clue systems, misdirection, and resolutions that reward careful listening across multiple tellings.
- **The loop structure serves the story.** Evidence carrying across retellings means early loops are discovery and later loops are revelation. The 5-minute constraint creates urgency without feeling artificial.
- **Full atmosphere.** Voice narration, AI illustrations, ambient soundscapes, and mood-reactive visuals — every sensory channel reinforces the story.
- **Dead simple to run.** One API key. One Docker container. No external services. Clone, build, listen.

## What we learned

- **AI storytelling is a performance art.** Native audio generation isn't TTS — the model controls rhythm, emphasis, and emotion. Prompting for *spoken* stories means thinking about delivery, not just words.
- **Multi-agent design is natural for storytelling.** A story has a voice, a visual imagination, an analytical eye, and a sense of atmosphere. Mapping each to a dedicated agent made the system intuitive to build and extend.
- **Time pressure makes stories better.** Without the 5-minute loop, listeners explore methodically. With it, they follow instinct and take risks — exactly what makes a mystery compelling.
- **Start generating before you have complete context.** The IllustratorAgent doesn't wait for the full scene description. The StoryAnalyst doesn't wait for the full passage. Early triggering makes the experience feel responsive and alive.

## What's next

- **Voice conversations** — let listeners speak directly to the narrator and characters using Gemini Live's bidirectional audio. A fully conversational storytelling experience.
- **Collaborative storytelling** — multiple listeners join the same story, each making independent choices that shape the shared narrative.
- **More stories and branching narratives** — expand the library with stories where different evidence combinations unlock entirely different story threads.
- **Custom story creation** — let users describe a premise and have the system generate a full mystery scenario with characters, clues, and a resolution.

## Try it out

**Live Demo:** https://echoes-cxotjai2ta-uc.a.run.app

```bash
git clone https://github.com/percyrico/echoes.git
cd echoes
cp .env.example .env   # add your GOOGLE_API_KEY
docker-compose up
```

Open `http://localhost:3000`. Pick a story. Listen closely. You have 5 minutes.

## Built with

Python, FastAPI, Google ADK, Google Gemini Live API (`gemini-2.5-flash-native-audio`), Gemini Flash (`gemini-2.5-flash-lite`), Gemini Image Generation (`gemini-2.0-flash-exp`), React, TypeScript, Tailwind CSS, Framer Motion, Zustand, WebSockets, Web Audio API, SQLite, aiosqlite, Docker, Google Cloud Run
