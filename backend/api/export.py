"""Game export endpoints for Echoes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/{session_id}")
async def get_export_data(session_id: str, request: Request):
    """Get all game data formatted for export / PDF generation on client side."""
    db = request.app.state.db
    session = await db.get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    game_state = session.get("game_state", {})

    return {
        "session_id": session_id,
        "scenario": session.get("scenario", ""),
        "game_state": game_state,
        "clues": game_state.get("clues", []),
        "loop_history": game_state.get("loop_history", []),
        "characters": game_state.get("characters", []),
        "is_complete": game_state.get("is_complete", False),
        "total_loops": game_state.get("current_loop", 1),
        "export_ready": True,
    }
