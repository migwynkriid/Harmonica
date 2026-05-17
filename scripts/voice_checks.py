import discord
from functools import wraps
from scripts.messages import create_embed
from scripts.constants import (
    EMBED_COLOR_ERROR,
    ERROR_NOT_IN_VOICE,
    ERROR_DIFFERENT_CHANNEL,
    ERROR_BOT_NOT_CONNECTED
)


def get_music_bot(ctx):
    """
    Get the MusicBot instance for the current guild.
    
    This function handles the lazy import of MusicBot to avoid circular imports.
    
    Args:
        ctx: The command context
        
    Returns:
        MusicBot: The server-specific MusicBot instance
    """
    from bot import MusicBot
    return MusicBot.get_instance(str(ctx.guild.id))


def requires_voice(check_bot_connected=True, check_same_channel=True):
    """
    Decorator that handles common voice channel checks for music commands.
    
    This decorator:
    1. Gets the MusicBot instance for the guild
    2. Performs voice state checks (configurable)
    3. Injects the music_bot into the function
    
    Args:
        check_bot_connected: If True, require bot to be in a voice channel
        check_same_channel: If True, require user to be in same channel as bot
        
    Returns:
        The decorated function with music_bot injected as first argument after self/ctx
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self_or_ctx, *args, **kwargs):
            # Handle both Cog methods (self, ctx) and standalone commands (ctx)
            if hasattr(self_or_ctx, 'bot'):
                self = self_or_ctx
                ctx = args[0]
                remaining_args = args[1:]
            else:
                self = None
                ctx = self_or_ctx
                remaining_args = args
            
            music_bot = get_music_bot(ctx)
            
            if check_bot_connected and check_same_channel:
                is_valid, error_embed = await check_voice_state(ctx, music_bot)
                if not is_valid:
                    await ctx.send(embed=error_embed)
                    return
            elif check_bot_connected:
                if not music_bot.voice_client or not music_bot.voice_client.channel:
                    await ctx.send(embed=create_embed("Error", ERROR_BOT_NOT_CONNECTED, color=EMBED_COLOR_ERROR, ctx=ctx))
                    return
            
            # Inject music_bot into the function call
            if self:
                return await func(self, ctx, music_bot, *remaining_args, **kwargs)
            else:
                return await func(ctx, music_bot, *remaining_args, **kwargs)
        return wrapper
    return decorator


def check_user_in_voice(ctx):
    """
    Check if the user is in a voice channel.
    
    Use this for commands that need the user to be in a voice channel
    but don't require the bot to already be connected (e.g., play, join).
    
    Args:
        ctx: The command context
        
    Returns:
        tuple: (is_valid, error_embed)
            - is_valid (bool): True if user is in a voice channel
            - error_embed (discord.Embed or None): Error embed if check fails
    """
    if not ctx.author.voice or not ctx.author.voice.channel:
        return False, create_embed(
            "Error",
            ERROR_NOT_IN_VOICE,
            color=EMBED_COLOR_ERROR,
            ctx=ctx
        )
    return True, None


async def check_voice_state(ctx, music_bot):
    """
    Check if both the bot and user are in the same voice channel.
    
    This function performs a series of checks to ensure that voice commands
    can only be used when both the bot and the user are in the same voice channel.
    It verifies:
    1. If the bot is currently in a voice channel
    2. If the user is in a voice channel
    3. If the user and bot are in the same voice channel
    
    If any check fails, the function returns False along with an appropriate
    error embed that can be sent to the user.
    
    Args:
        ctx: The command context containing information about the invoker
        music_bot: The music bot instance containing the voice client
        
    Returns:
        tuple: (is_valid, error_embed)
            - is_valid (bool): True if all checks pass, False otherwise
            - error_embed (discord.Embed or None): Error message embed if checks fail, None otherwise
    """
    # If MusicBot doesn't have a voice client but Discord does, try to sync them
    if not music_bot.voice_client and ctx.guild.voice_client:
        music_bot.voice_client = ctx.guild.voice_client
        
        # Try to find the correct instance if this one doesn't have current_song
        if not music_bot.current_song:
            from bot import MusicBot
            for instance_id, instance in MusicBot._instances.items():
                if instance.current_song:
                    music_bot.current_song = instance.current_song
                    music_bot.is_playing = True
                    break
    
    # Check if the bot is in a voice channel
    if not music_bot.voice_client or not music_bot.voice_client.channel:
        return False, create_embed("Error", ERROR_BOT_NOT_CONNECTED, color=EMBED_COLOR_ERROR, ctx=ctx)

    # Check if the user is in a voice channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        return False, create_embed("Error", ERROR_NOT_IN_VOICE, color=EMBED_COLOR_ERROR, ctx=ctx)

    # Check if user is in the same voice channel as the bot
    if ctx.author.voice.channel != music_bot.voice_client.channel:
        return False, create_embed("Error", ERROR_DIFFERENT_CHANNEL, color=EMBED_COLOR_ERROR, ctx=ctx)

    return True, None
