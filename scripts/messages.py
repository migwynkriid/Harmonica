import discord
from discord.ext import commands
from datetime import datetime
from scripts.constants import EMBED_COLOR_INFO

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

def create_embed(title, description, color=EMBED_COLOR_INFO, thumbnail_url=None, ctx=None):
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


async def send_queue_added_message(
    music_bot,
    ctx,
    song_info: dict,
    bot=None,
    color: int = 0x3498db
) -> discord.Message:
    """
    Send a standardized "Added to Queue" message.
    
    This helper creates consistent queue addition messages across the bot,
    handling loop detection for proper queue position display.
    
    Args:
        music_bot: The MusicBot instance
        ctx: The command context
        song_info: Song dictionary with 'title', 'url', 'thumbnail', optionally 'requester'
        bot: The Discord bot instance (for loop cog check). Uses ctx.bot if not provided.
        color: Embed color (default: info blue)
        
    Returns:
        discord.Message: The sent message (also stored in music_bot.queued_messages)
    """
    from scripts.playback import is_song_looping
    
    queue_pos = len(music_bot.queue)
    description = f"[🎵 {song_info['title']}]({song_info['url']})"
    
    # Show queue position if current song is not looping
    if music_bot.current_song:
        bot_instance = bot or getattr(ctx, 'bot', None)
        current_song_url = music_bot.current_song.get('url', '')
        if bot_instance and not is_song_looping(bot_instance, current_song_url):
            description += f"\nPosition in queue: {queue_pos}"
    
    # Create context with requester info if available
    requester = song_info.get('requester')
    ctx_with_requester = ctx
    if requester and hasattr(ctx, 'author') and requester != ctx.author:
        from scripts.playback import RequesterContext
        ctx_with_requester = RequesterContext(requester)
    
    queue_embed = create_embed(
        "Added to Queue",
        description,
        color=color,
        thumbnail_url=song_info.get('thumbnail'),
        ctx=ctx_with_requester
    )
    
    queue_msg = await ctx.send(embed=queue_embed)
    
    # Store message for cleanup when song plays
    async with music_bot.queued_messages_lock:
        music_bot.queued_messages[song_info['url']] = queue_msg
    
    return queue_msg
