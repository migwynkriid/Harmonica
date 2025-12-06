import discord
from discord.ext import commands
import time
from scripts.messages import create_embed
from scripts.duration import get_audio_duration
from scripts.ui_components import create_now_playing_view
from scripts.permissions import check_dj_role

class NowPlayingCog(commands.Cog):
    """
    Command cog for displaying the currently playing song.
    
    This cog handles the 'nowplaying' command, which shows information
    about the currently playing song, including progress bar and duration.
    """
    
    def __init__(self, bot):
        """
        Initialize the NowPlayingCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='nowplaying', aliases=['np'])
    @check_dj_role()
    async def nowplaying(self, ctx):
        """
        Show the currently playing song.
        
        This command displays detailed information about the currently playing song,
        including title, URL, thumbnail, and a progress bar showing the current
        playback position. For live streams, it shows a LIVE indicator instead.
        
        Args:
            ctx: The command context
        """
        # Access the music_bot from the global scope
        from bot import MusicBot
        
        # Get server-specific music bot instance
        server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
        
        if not server_music_bot:
            await ctx.send("Music bot is not initialized yet. Please wait a moment and try again.")
            return

        if not server_music_bot.current_song:
            await ctx.send(embed=create_embed("Error", "No song is currently playing!", color=0xe74c3c, ctx=ctx))
            return

        # Calculate elapsed time since song started
        current_position = int(time.time() - server_music_bot.playback_start_time) if server_music_bot.playback_start_time else 0
        
        # Get total duration and check if it's a stream
        is_stream = server_music_bot.current_song.get('is_stream', False)
        total_duration = server_music_bot.current_song.get('duration', 0) if not is_stream else 0
        
        # If duration is not set but we have a file path, try to get the duration
        if total_duration == 0 and not is_stream and 'file_path' in server_music_bot.current_song:
            file_path = server_music_bot.current_song['file_path']
            # Check if duration is in the cache
            total_duration = server_music_bot.duration_cache.get(file_path, 0)
            if total_duration == 0:
                # Calculate duration if not cached
                total_duration = await get_audio_duration(file_path)
                if total_duration > 0:
                    # Cache the duration for future use
                    server_music_bot.duration_cache[file_path] = total_duration
                    # Update the current song with the duration
                    server_music_bot.current_song['duration'] = total_duration
        
        # Format the current time in MM:SS format
        current_time = f"{int(current_position // 60):02d}:{int(current_position % 60):02d}"
        
        # Create the progress information based on whether it's a stream or not
        if is_stream:
            # For live streams, show a LIVE indicator with elapsed time
            progress_info = f"🔴 LIVE - {current_time}"
        else:
            # For regular songs, calculate percentage and create progress bar
            percentage = min((current_position / total_duration * 100) if total_duration > 0 else 0, 100)
            total_time = f"{int(total_duration // 60):02d}:{int(total_duration % 60):02d}"
            
            # Create progress bar with ▬ and :radio_button:
            # The bar has 20 segments, and we calculate which segment the playback is at
            position_segment = int((percentage / 5) + 0.5)  # Round to nearest segment (each segment is 5%)
            progress_bar = "▬" * position_segment + ":radio_button:" + "▬" * (20 - position_segment - 1)
            
            progress_info = f"[{progress_bar}]\n{current_time} / {total_time}"
        
        # Create description with title and progress
        description = f"[{server_music_bot.current_song['title']}]({server_music_bot.current_song['url']})\n\n{progress_info}"

        # Create the embed with song information
        embed = create_embed(
            "Now playing 🎵",
            description,
            color=0x3498db,
            thumbnail_url=server_music_bot.current_song.get('thumbnail'),
            ctx=ctx
        )

        # Create the view with buttons if enabled in config
        view = create_now_playing_view()
        # Only pass the view if it's not None
        kwargs = {'embed': embed}
        if view is not None:
            kwargs['view'] = view
        await ctx.send(**kwargs)

async def setup(bot):
    """
    Setup function to add the NowPlayingCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(NowPlayingCog(bot))