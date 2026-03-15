# Echoes

**A time-loop mystery game with real-time AI voice narration.**

You are a detective trapped in a time loop. A Gemini-powered narrator tells you the story out loud while you investigate, interrogate suspects, and gather clues. When time runs out, the loop resets — but your clues carry over. Collect enough key evidence and break the loop to solve the mystery.

**Live Demo:** https://echoes-cxotjai2ta-uc.a.run.app

---

## Quick Start

### Option 1: Docker (recommended)

```bash
git clone <repo-url>
cd echoes
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```
GOOGLE_API_KEY=your-gemini-api-key-here
```

Then run:

```bash
docker-compose up
```

Open http://localhost:3000 to play.

### Option 2: Local Development

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend** (in a separate terminal):

```bash
cd dashboard
npm install
npm run dev
```

Open http://localhost:5173 to play. The frontend proxies API/WebSocket requests to the backend on port 8000.

### Prerequisites

- Python 3.11+
- Node.js 20+
- A [Google Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)

No external databases or services required. Everything runs on SQLite locally.

---

## How to Play

### 1. Choose a Scenario

Pick from 8 detective mysteries, each with unique characters, clue networks, and solutions:

| Scenario | Premise |                                                                                                                                                                                                                      
  |----------|---------|                 
  | **The Last Train** | A midnight express hurtles through the storm. Someone on board won't survive the journey. |                                                                                                                          
  | **The Locked Room** | You wake up in a sealed Victorian study. The clock is ticking. The door won't open until you understand why. |
  | **The Dinner Party** | Eight guests. One poisoner. The dessert course is fatal. You have five minutes to find out who — before the chocolate soufflé arrives. |                                                                           
  | **The Signal** | A deep-space research station has gone silent. You're the only one awake. The signal it received is changing the station — and you. |
  | **The Crash** | A private plane went down in the mountains. All four passengers survived — but only three walked away. Someone sabotaged the aircraft. |
  | **The Heist** | A priceless diamond vanished during a museum gala. The security chief lies unconscious. The thief is still inside. |
  | **Room 414** | A tech CEO found dead in a luxury hotel room. The police say suicide. The evidence says otherwise. Someone in this hotel is lying. |
  | **The Factory** | An explosion at a chemical plant killed three workers. The company blames equipment failure. But someone disabled the safety systems — and someone else was paid to look away. |


### 2. Enter Your Name

The narrator will address you by name occasionally throughout the game.

### 3. Listen and Investigate

The narrator speaks to you in real time using Gemini's native audio generation. This is not text-to-speech — the AI controls pacing, emphasis, and tone naturally.

Each loop gives you **5 minutes**. Use them to:

- **Explore locations** — move around the crime scene
- **Examine evidence** — inspect objects, documents, and surroundings
- **Interrogate suspects** — ask characters questions and press for details
- **Make choices** — pick from context-aware options that appear after each narrator turn

The narrator reacts to your decisions. Bad ideas have consequences — try to bribe a guard and they might report you. Good instincts get rewarded with new leads.

### 4. Collect Clues

Clues are automatically detected from the narrator's dialogue. When you uncover key evidence, it appears in your clue panel with an illustration. Clues persist across loops — they are never lost.

Some clues are **key clues** (marked with a star). These are the critical pieces of evidence needed to solve the mystery.

### 5. Survive the Loop

When the 5-minute timer runs out, the loop resets. You get a scenario-specific death/failure scene, then can restart. Don't worry — all your clues carry over. Early loops are reconnaissance. Later loops are for closing in on the truth.

### 6. Break the Loop

Once you've collected enough key clues (typically 5-6), a **"Break the Loop"** button appears. Click it to confront the truth and solve the mystery. Present the right evidence and the loop breaks for good.

---

## Game Tips

- **Listen carefully.** The narrator drops clues in dialogue, not just in obvious "you found a clue" moments.
- **Try different approaches each loop.** Go left instead of right. Talk to a different suspect first. Time pressure means you can't do everything in one loop.
- **Bad choices are informative.** Getting caught, failing, or dying early still teaches you about the world. Every loop is progress.
- **Watch the mood indicator.** The ambient audio and visual effects shift with the story. Tension rising? You might be onto something.
- **Use the clue panel.** Review what you've found so far. Look for connections between clues from different loops.

---

## Architecture

```
Browser (React + Vite + Tailwind + Framer Motion)
    |
    WebSocket
    |
FastAPI Backend
    |
    +-- SessionManager (Orchestrator)
    |       Manages game state, loop timers, and agent coordination
    |
    +-- NarratorAgent (Gemini Live - gemini-2.5-flash-native-audio)
    |       Real-time voice narration with auto-continuation
    |
    +-- ClueDetectorAgent (gemini-2.5-flash-lite)
    |       Incremental transcript analysis for clue detection
    |
    +-- IllustratorAgent (gemini-2.0-flash-exp-image-generation)
    |       Scene, clue, death, and victory image generation
    |
    +-- ComposerAgent
            Mood-to-ambient-audio mapping with crossfade control
```

All agents run concurrently during each game turn. The IllustratorAgent triggers after just 80 characters of transcript so images arrive while the narrator is still speaking.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, Google ADK |
| Voice | Gemini Live API (`gemini-2.5-flash-native-audio-latest`) |
| Clue Detection | `gemini-2.5-flash-lite` |
| Image Generation | `gemini-2.0-flash-exp-image-generation` |
| Database | SQLite + aiosqlite |
| Frontend | React 18, TypeScript, Vite |
| Styling | Tailwind CSS, Framer Motion |
| State | Zustand |
| Audio | Web Audio API (gapless playback) |
| Deploy | Docker, Google Cloud Run |

---

## Project Structure

```
echoes/
├── backend/
│   ├── main.py                 # FastAPI app, WebSocket endpoint
│   ├── agents/
│   │   └── composer.py         # Mood-to-audio mapping agent
│   ├── services/
│   │   ├── session_manager.py  # Game engine + agent orchestrator
│   │   ├── gemini_live.py      # Gemini Live voice session
│   │   ├── clue_detector.py    # NLP clue extraction
│   │   ├── image_gen.py        # Scene image generation
│   │   └── world_db.py         # SQLite persistence
│   ├── models/
│   │   ├── schemas.py          # Pydantic models
│   │   └── scenarios.py        # 8 scenario definitions
│   └── api/
│       ├── scenarios.py        # Scenario list endpoint
│       ├── sessions.py         # Session CRUD
│       └── export.py           # Story export
├── dashboard/
│   └── src/
│       ├── components/         # React UI components
│       ├── hooks/              # WebSocket, audio, voice hooks
│       ├── store/              # Zustand game state
│       └── types/              # TypeScript definitions
├── Dockerfile                  # Production multi-stage build
├── docker-compose.yml          # Local dev setup
├── deploy.sh                   # Cloud Run deploy script
└── terraform/                  # GCP infrastructure as code
```

---

## Deployment

### Google Cloud Run

```bash
# Set your project
export PROJECT_ID=your-gcp-project-id

# Build and push
docker build -t gcr.io/$PROJECT_ID/echoes .
docker push gcr.io/$PROJECT_ID/echoes

# Deploy
gcloud run deploy echoes \
  --image gcr.io/$PROJECT_ID/echoes \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 1 \
  --timeout 300 \
  --set-env-vars "GOOGLE_API_KEY=your-key" \
  --port 8000
```

The production Dockerfile builds the React frontend and serves it from the FastAPI backend as a single container.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key from [Google AI Studio](https://ai.google.dev/) |
| `ENVIRONMENT` | No | Set to `development` for debug logging |

---

## License

MIT
