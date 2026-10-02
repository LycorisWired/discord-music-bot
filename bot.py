import asyncio
import logging
import os
from typing import override

import discord
from discord.ext import commands

from config import Config
from db import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("bot")


class DiscordBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = config.use_prefix_commands
        intents.voice_states = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(config.prefix)
            if config.use_prefix_commands
            else commands.when_mentioned,
            intents=intents,
            help_command=commands.DefaultHelpCommand()
            if config.use_prefix_commands
            else None,
        )
        self.config: Config = config
        self.db: Database = Database(config.db_path)

    @override
    async def close(self):
        await self.db.close()
        await super().close()

    @override
    async def setup_hook(self):
        await self.db.connect()

        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                extension = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(extension)
                    log.info("Loaded extension: %s", extension)
                except Exception:
                    log.exception("Failed to load extension: %s", extension)

        if self.config.guild_id:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Synced slash commands to guild %s", self.connect)
        else:
            # Global sync, use if you have the bot in multiple servers.
            # This can take up to an hour to propagate.
            await self.tree.sync()
            log.info("Synced slash commands globally")

    async def on_ready(self):
        log.info("Logged in as %s", self.user)


async def main():
    config = Config.from_env()
    bot = DiscordBot(config)
    async with bot:
        await bot.start(config.token)


if __name__ == "__main__":
    asyncio.run(main())
