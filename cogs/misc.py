import random
import re
from urllib.parse import urlparse, urlunparse

import discord
from discord import app_commands
from discord.ext import commands

from bot import DiscordBot

URL_RE = re.compile(r'https?://[^\s<>"\')\]]+', re.IGNORECASE)
FXEMBED = {
    "x.com": "vxtwitter.com",
    "twitter.com": "vxtwitter.com",
    "tiktok.com": "tnktok.com",
    "instagram.com": "oginstagram.com"
}

def swap_host(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    for domain, repl in FXEMBED.items():
        if host == domain or host.endswith("." + domain):
            return urlunparse(urlparse(url)._replace(netloc=repl))
    return None

class Misc(commands.Cog):
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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        print("listener fired")
        if message.author.bot:
            return
        print(repr(message.content))
        for url in URL_RE.findall(message.content):
            fixed = swap_host(url)
            if fixed:
                await message.channel.send(fixed)
                break

async def setup(bot: DiscordBot):
    await bot.add_cog(Misc(bot))
