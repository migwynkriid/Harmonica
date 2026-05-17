import discord
from scripts.messages import create_embed
from scripts.clear_queue import clear_download_queue
from scripts.constants import EMBED_COLOR_ERROR, EMBED_COLOR_SUCCESS, ERROR_BOT_NOT_CONNECTED

async def clear_queue_command(ctx, music_bot, position: int = None):
    """
    Clear songs from the queue.
    
    Args:
        ctx: The Discord context
        music_bot: The MusicBot instance
        position: Optional position to remove specific song (1-based index)
    
    Returns:
        None
    """
    if not ctx.voice_client:
        embed = create_embed("Error", ERROR_BOT_NOT_CONNECTED, EMBED_COLOR_ERROR, ctx=ctx)
        await ctx.send(embed=embed)
        return

    queue_length = len(music_bot.queue)
    
    if position is not None:
        # Handle removing specific song
        if position < 1 or position > queue_length:
            embed = create_embed(
                "Error",
                f"Nothing on queue order {position}.",
                EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.send(embed=embed)
            return
            
        # Remove specific song (convert to 0-based index)
        removed_song = music_bot.queue.pop(position - 1)
        embed = create_embed(
            "Song Removed",
            f"Removed song at position {position}: {removed_song['title']}",
            EMBED_COLOR_SUCCESS,
            ctx=ctx
        )
    else:
        # Clear entire queue except current song
        queue_length = len(music_bot.queue)
        
        # Use shared utility to clear download queue
        clear_download_queue(music_bot)
        
        # Clear the queue (use lock for thread safety)
        async with music_bot.queue_lock:
            music_bot.queue.clear()
        
        embed = create_embed(
            "Queue cleared",
            f"Successfully cleared {queue_length} songs from the queue!",
            EMBED_COLOR_SUCCESS,
            ctx=ctx
        )
    
    await ctx.send(embed=embed)
