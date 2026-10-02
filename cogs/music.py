from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from typing import cast

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

from bot import DiscordBot

log = logging.getLogger("cogs.music")

YTDL_OPTIONS = {
    "format": "bestaudio[abr<=96]/bestaudio",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "youtube_include_h1s_manifest": False,
    "youtube_include_dash_manifest": False,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


# YT-DLP helpers
async def search_ytdlp_async(query: str, ytdl_opts: dict) -> dict | None:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ytdl_opts))


def _extract(query: str, ytdl_opts: dict) -> dict | None:
    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:  # pyright: ignore[reportArgumentType]
        data = ydl.extract_info(query, download=False)
        return cast(dict, data)


@dataclass
class Track:
    title: str
    url: str
    stream_url: str
    duration: int | None
    requester: str


class GuildPlayer:
    def __init__(self, bot: commands.Bot, guild_id: int):
        self.bot = bot
        self.guild_id: int = guild_id
        self.queue: deque[Track] = deque()
        self.voice_client: discord.VoiceClient | None = None
        self.current: Track | None = None
        self.volume: float = 0.5
        self._skip_event: asyncio.Event = asyncio.Event()

    async def play_next(self):
        if not self.queue:
            self.current = None
            return

        if not self.voice_client:
            log.warning(
                "play_next called with no voice client in guild %s", self.guild_id
            )
            return

        self.current = self.queue.popleft()
        source = discord.FFmpegPCMAudio(self.current.stream_url, **FFMPEG_OPTIONS)  # type: ignore
        source = discord.PCMVolumeTransformer(source, volume=self.volume)

        def _after(error: Exception | None) -> None:
            if error:
                log.error("Playback error in guild %s: %s", self.guild_id, error)
            fut = asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)
            try:
                fut.result()
            except Exception:
                log.exception("Error advancing queue in guild %s", self.guild_id)

        self.voice_client.play(source, after=_after)


class Music(commands.Cog):
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer(self.bot, guild_id)
        return self.players[guild_id]

    async def _resolve(self, query: str) -> Track:
        data = await search_ytdlp_async(query, YTDL_OPTIONS)
        if data is None:
            raise ValueError(f"Could not resolve query: {query}")

        if "entries" in data:
            entries = list(data["entries"])
            if not entries:
                raise ValueError(f"No results found for query: {query}")
            data = entries[0]

        return Track(
            title=data.get("title", "Unknown title"),
            url=data.get("webpage_url", query),
            stream_url=data["url"],
            duration=data.get("duration"),
            requester="",
        )

    @app_commands.command(name="join", description="Join your current voice channel")
    async def join(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        if not interaction.user.voice:
            await interaction.response.send_message(
                "You need to be in a voice channel first.", ephemeral=True
            )
            return

        channel = interaction.user.voice.channel
        assert channel is not None

        player = self.get_player(interaction.guild_id)
        if player.voice_client is None:
            player.voice_client = await channel.connect()
        else:
            await player.voice_client.move_to(channel)
        await interaction.response.send_message(f"Joined **{channel.name}**.")

    @app_commands.command(
        name="leave", description="Leave the voice channel and clear the queue"
    )
    async def leave(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        player = self.get_player(interaction.guild_id)
        if player.voice_client:
            await player.voice_client.disconnect()
        player.queue.clear()
        player.current = None
        player.voice_client = None
        await interaction.response.send_message("Disconnected and cleared the queue.")

    @app_commands.command(name="play", description="Play a song by URL or search term")
    @app_commands.describe(query="YouTube/SoundCloud URL or a search term")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        if not interaction.user.voice:
            await interaction.followup.send("You need to be in a voice channel first.")
            return

        user_channel = interaction.user.voice.channel
        assert user_channel is not None
        player = self.get_player(interaction.guild_id)

        if player.voice_client is not None:
            if player.voice_client.channel != user_channel:
                await interaction.followup.send(
                    "I'm already playing in a different voice channel. "
                    "Use `/join` to move me to your channel, or join my channel.",
                    ephemeral=True,
                )
                return
        else:
            player.voice_client = await user_channel.connect()

        try:
            track = await self._resolve(query)
        except Exception as e:
            log.exception("Failed to resolve query: %s", query)
            await interaction.followup.send(f"Couldn't find or stream that: `{e}`")
            return

        track.requester = interaction.user.display_name

        if len(player.queue) >= self.bot.config.max_queue_size:
            await interaction.followup.send(
                "Queue is full, try again once it drains a bit."
            )
            return

        player.queue.append(track)

        if not player.voice_client.is_playing() and player.current is None:
            await player.play_next()
            await interaction.followup.send(f"Now playing: **{track.title}**")
        else:
            await interaction.followup.send(
                f"Queued: **{track.title}** (position {len(player.queue)})"
            )

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        # Prevent use in DMs
        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        player = self.get_player(interaction.guild_id)
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()  # triggers `after=` -> play_next
            await interaction.response.send_message("Skipped.")
        else:
            await interaction.response.send_message(
                "Nothing is playing.", ephemeral=True
            )

    @app_commands.command(name="pause", description="Pause playback")
    async def pause(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        player = self.get_player(interaction.guild_id)
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            await interaction.response.send_message("Paused.")
        else:
            await interaction.response.send_message(
                "Nothing is playing.", ephemeral=True
            )

    @app_commands.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        player = self.get_player(interaction.guild_id)
        if player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            await interaction.response.send_message("Resumed.")
        else:
            await interaction.response.send_message(
                "Nothing is paused.", ephemeral=True
            )

    @app_commands.command(name="queue", description="Show the current queue")
    async def show_queue(self, interaction: discord.Interaction):

        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        player = self.get_player(interaction.guild_id)
        if not player.current and not player.queue:
            await interaction.response.send_message("Queue is empty.")
            return

        lines = []
        if player.current:
            lines.append(f"**Now playing:** {player.current.title}")
        for i, track in enumerate(player.queue, start=1):
            lines.append(f"{i}. {track.title} (requested by {track.requester})")
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="volume", description="Set playback volume (0-100)")
    async def volume(
        self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 100]
    ):
        if not interaction.guild_id:
            await interaction.response.send_message(
                "This command must be used in a server.", ephemeral=True
            )
            return

        player = self.get_player(interaction.guild_id)
        player.volume = level / 100
        if player.voice_client and isinstance(
            player.voice_client.source, discord.PCMVolumeTransformer
        ):
            player.voice_client.source.volume = player.volume
        await interaction.response.send_message(f"Volume set to {level}%.")


async def setup(bot: DiscordBot):
    await bot.add_cog(Music(bot))
