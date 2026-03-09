"""Echoes — Time-Loop Mystery Storytelling Game Backend."""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import scenarios, sessions, export
from models.schemas import Scenario
from services.session_manager import SessionManager
from services.world_db import WorldDB

load_dotenv()  # Load from ./backend/.env
load_dotenv(dotenv_path="../.env")  # Fallback: load from root .env


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup app resources."""
    db = WorldDB()
    await db.initialize()
    app.state.db = db
    app.state.session_manager = SessionManager(db)
    yield
    await db.close()


app = FastAPI(title="Echoes", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scenarios.router, prefix="/api/scenarios", tags=["scenarios"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(export.router, prefix="/api/export", tags=["export"])

# Serve generated images
os.makedirs("data/images", exist_ok=True)
app.mount("/images", StaticFiles(directory="data/images"), name="images")

# Serve ambient audio assets
os.makedirs("assets/audio", exist_ok=True)
app.mount("/assets/audio", StaticFiles(directory="assets/audio"), name="audio")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "echoes"}


@app.websocket("/ws/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint for real-time game interaction.

    Handles:
    - start_game: Begin a new game with a scenario
    - user_text: Send text input to the narrator
    - user_audio: Binary frames with 0x01 prefix for audio
    - restart_loop: Restart the current loop after failure
    """
    await websocket.accept()
    manager: SessionManager = websocket.app.state.session_manager

    live_task = None

    try:
        while True:
            message = await websocket.receive()

            if "text" in message:
                data = json.loads(message["text"])
                msg_type = data.get("type", "")

                if msg_type == "start_game":
                    scenario_str = data.get("scenario", "last_train")
                    scenario = Scenario(scenario_str)
                    player_name = data.get("player_name", "Detective")

                    await manager.start_game(session_id, scenario, websocket, player_name=player_name)

                    # Start Gemini Live session for the first loop
                    live_task = asyncio.create_task(
                        manager.start_loop(session_id, websocket)
                    )

                elif msg_type == "user_text":
                    print(f"[WS] User text received: {data['text'][:80]}", flush=True)
                    await manager.handle_text_input(
                        session_id, data["text"], websocket
                    )

                elif msg_type == "break_loop":
                    await manager._handle_loop_break(session_id)

                elif msg_type == "restart_loop":
                    # Cancel old live task
                    if live_task and not live_task.done():
                        live_task.cancel()

                    live_task = asyncio.create_task(
                        manager.restart_loop(session_id, websocket)
                    )

            elif "bytes" in message:
                raw = message["bytes"]
                # First byte indicates type: 0x01 = audio
                if raw and len(raw) > 1:
                    frame_type = raw[0]
                    payload = raw[1:]
                    if frame_type == 0x01:
                        await manager.handle_audio(session_id, payload)

    except (WebSocketDisconnect, RuntimeError):
        if live_task and not live_task.done():
            live_task.cancel()
        await manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        if live_task and not live_task.done():
            live_task.cancel()
        await manager.disconnect(session_id)


# ---------------------------------------------------------------------------
# Serve frontend static files (production: combined Docker image)
# Only mount if the static directory exists so local dev is unaffected.
# ---------------------------------------------------------------------------
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.is_dir():
    # Serve static assets (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="frontend-assets")

    # SPA catch-all: serve index.html for any non-API, non-WS route
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the SPA index.html for all non-API routes."""
        # Try to serve the exact file first (e.g. favicon.ico, manifest.json)
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        # Fall back to index.html for SPA routing
        return FileResponse(STATIC_DIR / "index.html")
