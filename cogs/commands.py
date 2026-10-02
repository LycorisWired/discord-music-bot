import time

import discord
from discord import app_commands
from discord.ext import commands

from bot import DiscordBot


class Utility(commands.Cog):
    """This is a cog that sets a list of commands to be used for the bot."""

    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.started_at = time.time()

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! `{latency_ms}ms`")

    @app_commands.command(
        name="uptime", description="Show how long the bot has been running"
    )
    async def uptime(self, interaction: discord.Interaction):
        seconds = int(time.time() - self.started_at)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        await interaction.response.send_message(
            f"Up for {hours}h {minutes}m {seconds}s."
        )


async def setup(bot: DiscordBot):
    await bot.add_cog(Utility(bot))
