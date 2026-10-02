# discord-music-bot

A self-hosted Discord music bot built on `discord.py` + `yt-dlp` + `ffmpeg`, structured with Cogs so new command categories are easy to add over time. I plan on adding more features over time but don't expect regular updates.

## Features

- Slash commands: `/join`, `/leave`, `/play`, `/skip`, `/pause`, `/resume`, `/queue`, `/volume`
- Per-guild queue and volume, persisted to SQLite
- Auto-loading Cogs - drop a new file in `cogs/` to add a command category
- Dockerized, with ffmpeg baked into the image

## Requirements

- Python 3.12+ (only if running without Docker)
- Docker + Docker Compose (recommended)
- A Discord bot application ([Developer Portal](https://discord.com/developers/applications))

## Bot setup on the Discord Developer Portal

1. Create a new application, then add a **Bot** to it.
2. Under **Bot**, enable these **Privileged Gateway Intents**:
   - Server Members Intent - not required by default, only if you extend the bot to need member data
   - Message Content Intent - only required if `USE_PREFIX_COMMANDS=true`
3. Copy the bot token - you'll need it for `.env`.
4. Under **OAuth2 -> URL Generator**, select the `bot` and `applications.commands`
   scopes, and at minimum these bot permissions: `Connect`, `Speak`, `Send Messages`,
   `Use Slash Commands`. Use the generated URL to invite the bot to your server.

## Running with Docker (recommended)

```bash
git clone https://github.com/LycorisWired/discord-music-bot.git
cd discord-music-bot
cp .env.example .env
# edit .env and set DISCORD_TOKEN (and DEV_GUILD_ID while developing)
docker compose up --build -d
```

## Running without Docker

You'll need `ffmpeg` on your `PATH` (`pacman -S ffmpeg`, `apt install ffmpeg`, etc).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env
python bot.py
```

## Configuration

All configuration is via environment variables - see `.env.example` for the full list.

`DEV_GUILD_ID`: set it to your server's ID while
you're actively developing so slash command changes sync instantly.
Leave it blank for a public deployment, but note that global sync can take up to an hour to propagate but doesn't require specifying a guild.

## Adding new commands

Each command category lives in its own file under `cogs/`, following the
pattern in `cogs/utility.py`. `bot.py` loads every file in that directory
automatically on startup, so a new cog is just:

```python
# cogs/my_feature.py
from discord.ext import commands
from discord import app_commands
import discord

class MyFeature(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Say hello")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello!")

async def setup(bot):
    await bot.add_cog(MyFeature(bot))
```

Restart the bot and the command is live.

## Architecture notes

- **Audio pipeline**: `yt-dlp` resolves a direct stream URL and `ffmpeg`
  (invoked via `discord.py`'s `FFmpegPCMAudio`) transcodes it to Opus/PCM
  for Discord's voice gateway. This is fine for one bot serving a
  handful of servers. If this ever needs to scale to many concurrent
  servers, swapping to a [Lavalink](https://github.com/lavalink-devs/Lavalink)
  node is the natural next step and shouldn't require changing the
  command layer.
- **Persistence**: SQLite via `aiosqlite`, one row per guild in
  `guild_settings`. Good enough for config-scale data; if you outgrow it,
  swapping the `Database` class for Postgres is a contained change.

## Known limitations / things to expect

- `yt-dlp` occasionally breaks when YouTube changes something upstream.
  Keep it updated (`pip install -U yt-dlp`) if playback suddenly stops
  working.
- Queue state lives in memory (`GuildPlayer.queue`) and is lost on restart, even though settings persist. Persistence queue across restarts may be added in the future.

## License

  This project is licensed under the MIT License. Feel free to do whatever you'd like with the software.
