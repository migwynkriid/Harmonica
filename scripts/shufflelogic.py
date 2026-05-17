import random
from collections import deque
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
            
        # Convert to list, shuffle, and convert back to deque (with lock for thread safety)
        async with music_bot.queue_lock:
            queue_list = list(music_bot.queue)
            random.shuffle(queue_list)
            music_bot.queue = deque(queue_list)
        return True
        
    except Exception as e:
        print(f"Error shuffling queue: {e}")
        return False
