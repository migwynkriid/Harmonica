import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional, Any


async def update_or_send_message(
    bot_instance: Any,
    ctx: commands.Context,
    embed: discord.Embed,
    view: Optional[discord.ui.View] = None,
    force_new: bool = False
) -> discord.Message:
    """Update existing message or send a new one if none exists or if it's a new command"""
    try:
        if (force_new or 
            not bot_instance.current_command_msg or 
            ctx.author.id != bot_instance.current_command_author or 
            ctx.channel.id != bot_instance.current_command_msg.channel.id):
            
            bot_instance.current_command_msg = await ctx.send(embed=embed, view=view)
            bot_instance.current_command_author = ctx.author.id
        else:
            await bot_instance.current_command_msg.edit(embed=embed, view=view)
        
        return bot_instance.current_command_msg
    except Exception as e:
        print(f"Error updating message: {str(e)}")
        bot_instance.current_command_msg = await ctx.send(embed=embed, view=view)
        bot_instance.current_command_author = ctx.author.id
        return bot_instance.current_command_msg


def create_embed(
    title: str,
    description: str,
    color: int = 0x3498db,
    thumbnail_url: Optional[str] = None,
    ctx: Optional[commands.Context] = None
) -> discord.Embed:
        """Create a Discord embed with consistent styling"""
        embed = discord.Embed(
            title=title,
            description=description + "\n\u200b",  # Add blank line with zero-width space
            color=color,
            timestamp=datetime.now()  # Use current time when embed is created
        )
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        if ctx and hasattr(ctx, 'author') and ctx.author:
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )
        return embed


def should_send_now_playing(music_bot: Any, song_title: str) -> bool:
    """
    Determine if we should send a "now playing" message for this song.
    Returns True if we should send the message, False otherwise.
    """
    # Store current title for next comparison (needed for looped songs)
    music_bot.previous_song_title = song_title
    return True
