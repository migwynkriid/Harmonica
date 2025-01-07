import discord
from scripts.messages import create_embed

async def clear_queue_command(ctx, music_bot):
    """
    Clear all songs from the queue except the currently playing song.
    
    Args:
        ctx: The Discord context
        music_bot: The MusicBot instance
    
    Returns:
        None
    """
    if not ctx.voice_client:
        embed = create_embed("Error", "I'm not connected to a voice channel!", discord.Color.red(), ctx=ctx)
        await ctx.send(embed=embed)
        return

    # Store the length of queue before clearing
    queue_length = len(music_bot.queue)
    
    # Clear the queue
    music_bot.queue.clear()
    
    # Create success message
    embed = create_embed(
        "Queue Cleared",
        f"Successfully cleared {queue_length} songs from the queue!",
        discord.Color.green(),
        ctx=ctx
    )
    await ctx.send(embed=embed)
