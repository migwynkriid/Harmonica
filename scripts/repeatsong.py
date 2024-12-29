import discord
from discord.ext import commands
import asyncio

async def repeat_song(music_bot, ctx):
    """
    Function to handle song repetition
    Returns True if song should be repeated, False otherwise
    """
    if music_bot.current_song:
        music_bot.queue.append(music_bot.current_song)
        return True
    return False
