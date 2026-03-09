"""Session CRUD endpoints for Echoes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/")
async def list_sessions(request: Request):
    """List all game sessions."""
    db = request.app.state.db
    sessions = await db.list_sessions()
    return {"sessions": sessions}


@router.get("/{session_id}")
async def get_session(session_id: str, request: Request):
    """Get a specific session's game state."""
    db = request.app.state.db
    session = await db.get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return {"session": session}


@router.delete("/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Delete a game session."""
    db = request.app.state.db
    await db.delete_session(session_id)
    return {"status": "deleted"}
