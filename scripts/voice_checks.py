import discord
from scripts.messages import create_embed

async def check_voice_state(ctx, music_bot):
    """
    Check if both the bot and user are in the same voice channel.
    Returns (bool, discord.Embed or None) - (is_valid, error_embed)
    """
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
