"""WorldDB — SQLite persistence for Echoes game sessions."""

import json
import os
from datetime import datetime

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "data/echoes.db")


class WorldDB:
    """Async SQLite database for game session persistence."""

    def __init__(self):
        self.db_path = DB_PATH
        self._db: aiosqlite.Connection | None = None

    async def initialize(self):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._create_tables()

    async def _create_tables(self):
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                scenario TEXT NOT NULL,
                game_state TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        await self._db.commit()

    async def save_session(self, session_id: str, scenario: str, game_state: dict):
        """Save or update a game session."""
        now = datetime.utcnow().isoformat()
        await self._db.execute(
            """INSERT INTO sessions (id, scenario, game_state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   game_state = excluded.game_state,
                   updated_at = excluded.updated_at""",
            (session_id, scenario, json.dumps(game_state), now, now),
        )
        await self._db.commit()

    async def get_session(self, session_id: str) -> dict | None:
        """Load a game session by ID."""
        async with self._db.execute(
            "SELECT id, scenario, game_state, created_at FROM sessions WHERE id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "scenario": row[1],
                    "game_state": json.loads(row[2]),
                    "created_at": row[3],
                }
        return None

    async def list_sessions(self) -> list[dict]:
        """List all sessions."""
        async with self._db.execute(
            "SELECT id, scenario, created_at, updated_at FROM sessions ORDER BY updated_at DESC",
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {"id": r[0], "scenario": r[1], "created_at": r[2], "updated_at": r[3]}
                for r in rows
            ]

    async def delete_session(self, session_id: str):
        """Delete a session."""
        await self._db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
