from discord.ext import commands
import sys
import os
import time
from scripts.messages import create_embed
from scripts.ui_components import create_now_playing_view
from scripts.permissions import check_dj_role

# Add the parent directory to sys.path to allow importing from bot
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

class NowPlayingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='nowplaying', aliases=['np'])
    @check_dj_role()
    async def nowplaying(self, ctx):
        """Show the currently playing song"""
        # Access the music_bot from the global scope
        from bot import music_bot
        
        if not music_bot:
            await ctx.send("Music bot is not initialized yet. Please wait a moment and try again.")
            return

        if not music_bot.current_song:
            await ctx.send(embed=create_embed("Error", "No song is currently playing!", color=0xe74c3c, ctx=ctx))
            return

        # Calculate elapsed time since song started
        current_position = int(time.time() - music_bot.playback_start_time) if music_bot.playback_start_time else 0
        
        # Get total duration and check if it's a stream
        is_stream = music_bot.current_song.get('is_stream', False)
        total_duration = music_bot.current_song.get('duration', 0) if not is_stream else 0
        
        # Format the current time
        current_time = f"{int(current_position // 60):02d}:{int(current_position % 60):02d}"
        
        # Create the progress information based on whether it's a stream or not
        if is_stream:
            progress_info = f"🔴 LIVE - {current_time}"
        else:
            # Calculate percentage and create progress bar
            percentage = min((current_position / total_duration * 100) if total_duration > 0 else 0, 100)
            total_time = f"{int(total_duration // 60):02d}:{int(total_duration % 60):02d}"
            
            # Create progress bar with ▬ and :radio_button:
            position_segment = int((percentage / 5) + 0.5)  # Round to nearest segment (each segment is 5%)
            progress_bar = "▬" * position_segment + ":radio_button:" + "▬" * (20 - position_segment - 1)
            
            progress_info = f"[{progress_bar}]\n{current_time} / {total_time}"
        
        # Create description with title and progress
        description = f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})\n\n{progress_info}"

        embed = create_embed(
            "Now playing 🎵",
            description,
            color=0x3498db,
            thumbnail_url=music_bot.current_song.get('thumbnail'),
            ctx=ctx
        )

        # Create the view with buttons if enabled
        view = create_now_playing_view()
        # Only pass the view if it's not None
        kwargs = {'embed': embed}
        if view is not None:
            kwargs['view'] = view
        await ctx.send(**kwargs)

async def setup(bot):
    await bot.add_cog(NowPlayingCog(bot))