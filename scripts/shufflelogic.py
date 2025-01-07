import random
from discord.ext import commands

async def shuffle_queue(ctx, music_bot):
    """
    Shuffle all songs in the queue randomly.
    
    Args:
        ctx: The Discord context
        music_bot: The MusicBot instance
    
    Returns:
        bool: True if shuffle was successful, False if queue is empty
    """
    try:
        if not music_bot.queue:
            return False
            
        # Create a copy of the queue and shuffle it
        random.shuffle(music_bot.queue)
        return True
        
    except Exception as e:
        print(f"Error shuffling queue: {e}")
        return False
