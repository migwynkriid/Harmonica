"""
Base functionality for seek commands (forward/rewind).

This module provides the shared logic for both forward and rewind commands
to avoid code duplication (DRY principle).
"""

import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import check_voice_state
from scripts.seek import seek_audio


async def execute_seek_command(ctx, music_bot, seconds, direction):
    """
    Execute a seek operation (forward or rewind).
    
    This is a shared function that handles the common logic for both
    forward and rewind commands.
    
    Args:
        ctx: The command context
        music_bot: The music bot instance
        seconds (int): Number of seconds to seek
        direction (str): Either "forward" or "rewind"
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate seconds parameter
        if seconds <= 0:
            action = "Forward" if direction == "forward" else "Rewind"
            await ctx.send(embed=create_embed(
                "Error", 
                f"{action} amount must be greater than 0 seconds!", 
                color=0xe74c3c, 
                ctx=ctx
            ))
            return False
            
        # Check voice state (user must be in same voice channel as bot)
        is_valid, error_embed = await check_voice_state(ctx, music_bot)
        if not is_valid:
            await ctx.send(embed=error_embed)
            return False

        # Perform the seek operation
        success, message, new_position = await seek_audio(ctx, music_bot, seconds, direction=direction)
        
        if not success:
            await ctx.send(embed=create_embed("Error", message, color=0xe74c3c, ctx=ctx))
            return False
        
        # Send success message
        current_song = music_bot.current_song
        emoji = "⏩" if direction == "forward" else "⏪"
        title = "Fast Forward" if direction == "forward" else "Rewind"
        direction_verb = "forward" if direction == "forward" else "backward"
        
        embed = create_embed(
            f"{emoji} {title}",
            f"Skipped {direction_verb} {seconds} seconds to {message}\n[{current_song['title']}]({current_song['url']})",
            color=0x3498db,
            ctx=ctx
        )
        if 'thumbnail' in current_song:
            embed.set_thumbnail(url=current_song['thumbnail'])
        await ctx.send(embed=embed)
        return True

    except ValueError:
        await ctx.send(embed=create_embed(
            "Error", 
            "Invalid number of seconds! Please provide a valid integer.", 
            color=0xe74c3c, 
            ctx=ctx
        ))
        return False
    except Exception as e:
        action_desc = "seeking forward" if direction == "forward" else "rewinding"
        await ctx.send(embed=create_embed(
            "Error", 
            f"An error occurred while {action_desc}: {str(e)}", 
            color=0xe74c3c, 
            ctx=ctx
        ))
        return False
