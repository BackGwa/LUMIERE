import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import sys
import os
import logging

sys.path.append(os.path.dirname(__file__))

from utils.config import config, ConfigError
from utils.language import lang
from commands.create import create_image_command, get_quality_choices, get_ratio_choices

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LumiereBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        
        super().__init__(
            command_prefix="",
            intents=intents,
            help_command=None
        )
        
    async def setup_hook(self):
        try:
            logger.info("Setting up slash commands...")
            guild_ids = config.get_guild_ids()
            if guild_ids:
                logger.info(f"Syncing commands to guilds: {guild_ids}")
                for guild_id in guild_ids:
                    self.tree.copy_global_to(guild=discord.Object(id=guild_id))
                    await self.tree.sync(guild=discord.Object(id=guild_id))
            else:
                logger.info("Syncing commands globally...")
                await self.tree.sync()
            logger.info("Slash commands setup complete")
        except ConfigError as e:
            logger.error(f"Config error during setup: {e}")
            await self.tree.sync()
        except Exception as e:
            logger.error(f"Error during setup: {e}", exc_info=True)
    
    async def on_ready(self):
        logger.info(f'{self.user} connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')

bot = LumiereBot()

@bot.tree.command(name="create", description=lang.get("discord.commands.create.description"))
@app_commands.describe(
    prompt=lang.get("discord.commands.create.prompt_description"),
    ratio=lang.get("discord.commands.create.ratio_description"),
    quality=lang.get("discord.commands.create.quality_description"),
    private=lang.get("discord.commands.create.private_description"),
    sensitive=lang.get("discord.commands.create.sensitive_description")
)
async def create_image(
    interaction: discord.Interaction,
    prompt: str,
    ratio: Optional[str] = None,
    quality: Optional[str] = None,
    private: bool = False,
    sensitive: bool = False
):
    await create_image_command(interaction, prompt, ratio, quality, private, sensitive)

create_image.autocomplete('quality')(get_quality_choices)
create_image.autocomplete('ratio')(get_ratio_choices)

def start_bot():
    try:
        logger.info("Starting Discord bot...")
        token = config.get_discord_token()
        logger.info("Token obtained, connecting...")
        bot.run(token)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    try:
        start_bot()
    except KeyboardInterrupt:
        sys.exit(0)