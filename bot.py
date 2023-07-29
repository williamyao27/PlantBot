# ==================================================================================================
# PlantBot                           Created by William Yao                  Last updated 2023-04-01
# --------------------------------------------------------------------------------------------------
# PlantBot is a minigame bot that allows servers to collaboratively grow a plant and harvest fruit.
# This is the main file to run PlantBot on all connected servers.
# ==================================================================================================
import os
import discord

import dotenv
from discord.ext import commands

from plant import PlantManager


# ==================================================================================================
# INITIALIZE BOT
# ==================================================================================================
# Retrieve bot information from .env
dotenv.load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
guild_ids = [int(guild_id) for guild_id in GUILD.split(",")]

# Create bot with full permissions
intents = discord.Intents().all()
bot = commands.Bot(command_prefix="$", intents=intents)

# Initialize server-specific plant managers
plant_managers = {}


@bot.event
async def on_ready() -> None:
    """Print each of the bot's connected servers and initialize server-specific data.
    """
    print(f"{bot.user} is connected to the following guild(s):\n")
    for gid in guild_ids:
        # Print list of connected guilds
        print(f"{bot.get_guild(gid)} (id: {gid})")

        # Initialize data for this server
        plant_managers[gid] = PlantManager(gid)


# ==================================================================================================
# COMMANDS
# ==================================================================================================
@bot.command()
async def plant(ctx, *args) -> None:
    """Process command to interact with the server plant in the proper server context.
    """
    gid = ctx.guild.id
    await plant_managers[gid].process_cmd(ctx, *args)


# ==================================================================================================
# EVENT HANDLERS
# ==================================================================================================
@bot.event
async def on_message(message) -> None:
    """Process incoming messages.
    """
    # Return early if bot is responding to itself
    if message.author == bot.user:
        return

    # Process commands
    await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction, reactor) -> None:
    """Process incoming reactions.
    """
    # Return early if bot is reacting to itself
    if reactor == bot.user:
        return

    # Process reaction
    gid = reaction.message.guild.id
    await plant_managers[gid].process_reaction(reaction, reactor)


# ==================================================================================================
# RUN BOT
# ==================================================================================================
bot.run(TOKEN)
