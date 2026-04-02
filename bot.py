import sys
import os
# Ensure the app directory is in the Python path so cogs can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import traceback
import logging
from dotenv import load_dotenv

load_dotenv()

TOKEN    = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# ─────────────────────────────────────────────
#  Logging Setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("amate")

# ─────────────────────────────────────────────
#  Intents
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.members         = True
intents.message_content = True
intents.guilds          = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ─────────────────────────────────────────────
#  Cog Loader
# ─────────────────────────────────────────────
COGS = ["cogs.verify", "cogs.tickets"]

async def load_cogs():
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            log.info(f"✅ Loaded cog: {cog}")
        except Exception as e:
            log.error(f"❌ Failed to load {cog}: {e}\n{traceback.format_exc()}")

# ─────────────────────────────────────────────
#  Global Error Handler — Slash Commands
# ─────────────────────────────────────────────
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # Unwrap CheckFailure wrappers
    original = getattr(error, "original", error)

    log.error(
        f"[SLASH ERROR] /{interaction.command.name if interaction.command else '?'} "
        f"by {interaction.user} ({interaction.user.id}): {original}\n{traceback.format_exc()}"
    )

    # User-facing messages per error type
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ Du hast keine Berechtigung für diesen Befehl."
    elif isinstance(error, app_commands.BotMissingPermissions):
        msg = "❌ Ich habe nicht die nötigen Berechtigungen dafür."
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = f"⏳ Bitte warte noch **{error.retry_after:.1f}s** bevor du den Befehl erneut nutzt."
    elif isinstance(error, app_commands.NoPrivateMessage):
        msg = "❌ Dieser Befehl kann nicht in DMs genutzt werden."
    elif isinstance(original, discord.Forbidden):
        msg = "❌ Ich habe keine Berechtigung, diese Aktion auszuführen."
    elif isinstance(original, discord.NotFound):
        msg = "❌ Etwas wurde nicht gefunden (möglicherweise bereits gelöscht)."
    elif isinstance(original, discord.HTTPException):
        msg = f"❌ Discord-Fehler: `{original.status}` — bitte versuche es später erneut."
    else:
        msg = "❌ Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es erneut."

    embed = discord.Embed(description=msg, color=0xFF4444)

    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        pass  # Interaction already expired or unreachable

# ─────────────────────────────────────────────
#  Global Error Handler — Prefix Commands
# ─────────────────────────────────────────────
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    original = getattr(error, "original", error)
    log.error(f"[CMD ERROR] {ctx.command} by {ctx.author}: {original}\n{traceback.format_exc()}")

# ─────────────────────────────────────────────
#  Unhandled Task / Asyncio Exceptions
# ─────────────────────────────────────────────
def handle_task_exception(task: asyncio.Task):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.error(f"[TASK ERROR] Unhandled exception in task '{task.get_name()}': {e}\n{traceback.format_exc()}")

# ─────────────────────────────────────────────
#  Events
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        log.info(f"⚡ Synced {len(synced)} slash command(s)")
    except Exception as e:
        log.error(f"Sync error: {e}\n{traceback.format_exc()}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Amate"
        )
    )
    log.info(f"🚀 Online as {bot.user}  |  Guild lock: {GUILD_ID}")

@bot.event
async def on_guild_join(guild: discord.Guild):
    if GUILD_ID and guild.id != GUILD_ID:
        log.warning(f"🚫 Unauthorized guild — leaving: {guild.name} ({guild.id})")
        await guild.leave()

@bot.event
async def on_error(event: str, *args, **kwargs):
    log.error(f"[EVENT ERROR] Unhandled exception in event '{event}':\n{traceback.format_exc()}")

# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────
async def main():
    async with bot:
        await load_cogs()
        if not TOKEN:
            raise ValueError("[AMATE] DISCORD_TOKEN is not set in .env!")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
