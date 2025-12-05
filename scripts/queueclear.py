import discord
from scripts.messages import create_embed
from scripts.clear_queue import clear_download_queue

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
        embed = create_embed("Error", "I'm not connected to a voice channel!", discord.Color.red(), ctx=ctx)
        await ctx.send(embed=embed)
        return

    queue_length = len(music_bot.queue)
    
    if position is not None:
        # Handle removing specific song
        if position < 1 or position > queue_length:
            embed = create_embed(
                "Error",
                f"Nothing on queue order {position}. Please specify a number between 1 and {queue_length}",
                discord.Color.red(),
                ctx=ctx
            )
            await ctx.send(embed=embed)
            return
            
        # Remove specific song (convert to 0-based index)
        removed_song = music_bot.queue.pop(position - 1)
        embed = create_embed(
            "Song Removed",
            f"Removed song at position {position}: {removed_song['title']}",
            discord.Color.green(),
            ctx=ctx
        )
    else:
        # Clear entire queue except current song
        queue_length = len(music_bot.queue)
        
        # Use shared utility to clear download queue
        clear_download_queue(music_bot)
        
        # Clear the queue
        music_bot.queue.clear()
        
        embed = create_embed(
            "Queue cleared",
            f"Successfully cleared {queue_length} songs from the queue!",
            discord.Color.green(),
            ctx=ctx
        )
    
    await ctx.send(embed=embed)
