import discord

async def update_activity(bot, current_song=None, is_playing=False):
    """Update the bot's activity status"""
    try:
        if bot:
            if current_song and is_playing:
                activity = discord.Activity(
                    type=discord.ActivityType.playing,
                    name=f"🎵 {current_song['title']}"
                )
            else:
                activity = discord.Activity(
                    type=discord.ActivityType.playing,
                    name="nothing! use !play "
                )
            await bot.change_presence(activity=activity)
    except Exception as e:
        print(f"Error updating activity: {str(e)}")
