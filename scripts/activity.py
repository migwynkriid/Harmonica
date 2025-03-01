import discord
from scripts.config import load_config, config_vars

async def update_activity(bot, current_song=None, is_playing=False):
    """
    Update the bot's activity status based on configuration settings.
    
    This function updates the bot's Discord presence/activity status based on
    whether a song is currently playing and the SHOW_ACTIVITY_STATUS configuration.
    
    If SHOW_ACTIVITY_STATUS is True (default):
      - When a song is playing, it shows the song title
      - When no song is playing, it shows "nothing! use {prefix}play"
    
    If SHOW_ACTIVITY_STATUS is False:
      - Always shows "use {prefix}help" regardless of playback status
    
    Args:
        bot: The Discord bot instance
        current_song (dict, optional): Dictionary containing information about the current song
        is_playing (bool, optional): Boolean indicating if a song is currently playing
        
    Returns:
        None
    """
    try:
        if bot and hasattr(bot, 'change_presence'):
            prefix = config_vars.get('PREFIX', '!')
            
            # Check if activity status updates are enabled in configuration
            # The config value is a top-level flattened key in config_vars
            show_activity = config_vars.get('SHOW_ACTIVITY_STATUS', True)
            
            if show_activity:
                # Normal behavior - show current song or play command
                if current_song and is_playing:
                    activity = discord.Activity(
                        type=discord.ActivityType.playing,
                        name=f" {current_song['title']}"
                    )
                else:
                    activity = discord.Activity(
                        type=discord.ActivityType.playing,
                        name=f"nothing! use {prefix}play "
                    )
            else:
                # When activity status is disabled, only show help message
                activity = discord.Activity(
                    type=discord.ActivityType.playing,
                    name=f"use {prefix}help"
                )
                
            await bot.change_presence(activity=activity)
    except Exception as e:
        print(f"Error updating activity: {str(e)}")
