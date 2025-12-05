import discord
from discord.ext import commands

async def repeat_song(music_bot, ctx):
    """
    Handle song repetition by adding the current song back to the queue.
    
    This function implements the repeat functionality for the music bot.
    When called, it takes the currently playing song and adds it to the end
    of the queue so it will play again after all other songs in the queue.
    
    Args:
        music_bot: The music bot instance containing the current song and queue
        ctx: The command context
        
    Returns:
        bool: True if a song was successfully added for repetition, False if there
              was no current song to repeat
    """
    if music_bot.current_song:
        music_bot.queue.append(music_bot.current_song)
        return True
    return False
