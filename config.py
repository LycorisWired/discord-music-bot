"""
All configuration comes from environment variables so nothing sensitive
ever lives in source control. Copy .env.example to .env and fill it in.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    token: str
    prefix: str
    use_prefix_commands: bool
    guild_id: int | None  # set for fast dev sync; leave unset for a public fork
    db_path: str
    default_volume: float
    max_queue_size: int

    @classmethod
    def from_env(cls) -> Config:
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise RuntimeError(
                "DISCORD_TOKEN is not set. Copy .env.example to .env and "
                "fill in your bot token from the Discord Developer Portal."
            )

        guild_id_raw = os.getenv("DEV_GUILD_ID")

        return cls(
            token=token,
            prefix=os.getenv("COMMAND_PREFIX", "!"),
            use_prefix_commands=_get_bool("USE_PREFIX_COMMANDS", False),
            guild_id=int(guild_id_raw) if guild_id_raw else None,
            db_path=os.getenv("DB_PATH", "data/bot.sqlite3"),
            default_volume=float(os.getenv("DEFAULT_VOLUME", "0.5")),
            max_queue_size=int(os.getenv("MAX_QUEUE_SIZE", "200")),
        )
