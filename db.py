"""
Tiny async sqlite wrapper for per-guild settings (volume, DJ role, etc).
"""

import os
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    volume REAL NOT NULL DEFAULT 0.3,
    dj_role_id INTEGER,
    music_channel_id INTEGER
);
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: aiosqlite.Connection | None

    async def connect(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        await self._conn.execute(SCHEMA)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def get_guild_settings(self, guild_id: int) -> dict[str, Any]:
        assert self._conn
        cur = await self._conn.execute(
            "SELECT volume, dj_role_id, music_channel_id FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return {"volume": 0.3, "dj_role_id": None, "music_channel_id": None}
        return {"volume": row[0], "dj_role_id": row[1], "music_channel_id": row[2]}

    async def set_guild_setting(self, guild_id: int, key: str, value: Any):
        assert self._conn
        current = await self.get_guild_settings(guild_id)
        current[key] = value
        await self._conn.execute(
            """
            INSERT INTO guild_settings (guild_id, volume, dj_role_id, music_channel_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                volume = excluded.volume,
                dj_role_id = excluded.dj_role_id,
                music_channel_id = excluded.music_channel_id
            """,
            (
                guild_id,
                current["volume"],
                current["dj_role_id"],
                current["music_channel_id"],
            ),
        )
        await self._conn.commit()
