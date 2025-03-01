import discord
from scripts.messages import create_embed

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
        return False, create_embed("Error", "I'm not in a voice channel", color=0xe74c3c, ctx=ctx)

    # Check if the user is in a voice channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        return False, create_embed("Error", "You must be in a voice channel to use this command", color=0xe74c3c, ctx=ctx)

    # Check if user is in the same voice channel as the bot
    if ctx.author.voice.channel != music_bot.voice_client.channel:
        return False, create_embed("Error", "You must be in the same voice channel as me to use this command", color=0xe74c3c, ctx=ctx)

    return True, None
