import random

import discord
from discord import app_commands
from discord.ext import commands

from bot import DiscordBot


class Fun(commands.Cog):
    def __init__(self, bot: DiscordBot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll a die")
    @app_commands.describe(sides="Which die to roll", count="How many times")
    @app_commands.choices(
        sides=[
            app_commands.Choice(name="d4", value=4),
            app_commands.Choice(name="d6", value=6),
            app_commands.Choice(name="d8", value=8),
            app_commands.Choice(name="d12", value=12),
            app_commands.Choice(name="d20", value=20),
        ]
    )
    async def roll(
        self,
        interaction: discord.Interaction,
        sides: app_commands.Choice[int],
        count: app_commands.Range[int, 1, 20] = 1,
    ):
        rolls = [random.randint(1, sides.value) for _ in range(count)]
        total = sum(rolls)
        rolls_str = ", ".join(str(r) for r in rolls)
        _ = await interaction.response.send_message(
            f"Rolling {count}d{sides.value}: [{rolls_str}] — total: **{total}**"
        )


async def setup(bot: DiscordBot):
    await bot.add_cog(Fun(bot))
