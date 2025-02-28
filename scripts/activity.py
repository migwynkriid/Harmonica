import discord
from scripts.config import load_config

async def update_activity(bot, current_song=None, is_playing=False):
    """Update the bot's activity status"""
    try:
        if bot and hasattr(bot, 'change_presence'):
            if current_song and is_playing:
                activity = discord.Activity(
                    type=discord.ActivityType.playing,
                    name=f" {current_song['title']}"
                )
            else:
                prefix = load_config()['PREFIX']
                activity = discord.Activity(
                    type=discord.ActivityType.playing,
                    name=f"nothing! use {prefix}play "
                )
            await bot.change_presence(activity=activity)
    except Exception as e:
        print(f"Error updating activity: {str(e)}")
