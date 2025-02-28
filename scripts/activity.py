import discord
from scripts.config import load_config

async def update_activity(bot, current_song=None, is_playing=False):
    """
    Update the bot's activity status.
    
    This function updates the bot's Discord presence/activity status based on
    whether a song is currently playing. If a song is playing, it shows the
    song title. Otherwise, it shows a message prompting users to use the play command.
    
    Args:
        bot: The Discord bot instance
        current_song (dict, optional): Dictionary containing information about the current song
        is_playing (bool, optional): Boolean indicating if a song is currently playing
        
    Returns:
        None
    """
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
