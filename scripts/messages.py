import discord
from discord.ext import commands
from datetime import datetime

async def update_or_send_message(bot_instance, ctx, embed, view=None, force_new=False):
    """
    Update existing message or send a new one if none exists or if it's a new command.
    
    This function manages Discord message updates to avoid spamming the channel with
    multiple messages for the same command. It will update an existing message if
    it's from the same user and in the same channel, or create a new message otherwise.
    
    Args:
        bot_instance: The bot instance containing message tracking variables
        ctx: The command context
        embed: The embed to send or update
        view: Optional view (buttons/components) to attach to the message
        force_new: If True, always send a new message regardless of existing messages
        
    Returns:
        discord.Message: The sent or updated message
    """
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

def create_embed(title, description, color=0x3498db, thumbnail_url=None, ctx=None):
    """
    Create a Discord embed with consistent styling.
    
    This function creates a standardized Discord embed with consistent styling
    across the bot. It includes a title, description, color, optional thumbnail,
    and footer with the requester's name and avatar if context is provided.
    
    Args:
        title: The embed title
        description: The embed description
        color: The color of the embed (default: blue)
        thumbnail_url: Optional URL for the embed thumbnail
        ctx: Optional command context for adding requester info to the footer
        
    Returns:
        discord.Embed: The created embed
    """
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

def should_send_now_playing(music_bot, song_title):
    """
    Determine if we should send a "now playing" message for this song.
    
    This function decides whether to send a "now playing" message for the
    current song. It stores the current song title for future comparisons,
    which is useful for handling looped songs.
    
    Args:
        music_bot: The music bot instance
        song_title: The title of the current song
        
    Returns:
        bool: True if we should send the message, False otherwise
    """
    # Store current title for next comparison (needed for looped songs)
    music_bot.previous_song_title = song_title
    return True
