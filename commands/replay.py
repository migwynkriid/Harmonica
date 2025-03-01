import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.config import FFMPEG_OPTIONS
from scripts.activity import update_activity
from scripts.voice_checks import check_voice_state
import time

class ReplayCog(commands.Cog):
    """
    Command cog for replaying the current song.
    
    This cog provides the 'replay' command, which restarts the currently
    playing song from the beginning without stopping playback.
    """
    
    def __init__(self, bot):
        """
        Initialize the ReplayCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self._last_member = None

    @commands.command(name='replay')
    @check_dj_role()
    async def replay(self, ctx):
        """
        Restart the currently playing song from the beginning.
        
        This command restarts the currently playing song from the beginning
        without removing it from the queue or stopping playback. It works by
        creating a new audio source with the seek position set to 0.
        This command requires DJ permissions.
        
        Args:
            ctx: The command context
        """
        from bot import MusicBot
        music_bot = MusicBot.get_instance(str(ctx.guild.id))
        
        # If MusicBot doesn't have a voice client but Discord does, try to sync them
        if not music_bot.voice_client and ctx.guild.voice_client:
            music_bot.voice_client = ctx.guild.voice_client
            
            # Try to find the correct instance if this one doesn't have current_song
            if not music_bot.current_song:
                for instance_id, instance in MusicBot._instances.items():
                    if instance.current_song:
                        music_bot.current_song = instance.current_song
                        music_bot.is_playing = True
                        break
        
        try:
            # Check voice state
            is_valid, error_embed = await check_voice_state(ctx, music_bot)
            if not is_valid:
                await ctx.send(embed=error_embed)
                return

            # Check if there's a song playing
            if not music_bot.current_song:
                await ctx.send(embed=create_embed("Error", "No song is currently playing!", color=0xe74c3c, ctx=ctx))
                return

            # Get current song info
            current_song = music_bot.current_song
            
            # Create a new FFmpeg audio source with seek set to beginning
            ffmpeg_options = FFMPEG_OPTIONS.copy()
            ffmpeg_options['options'] = ffmpeg_options.get('options', '') + ' -ss 0'
            
            # Create new source with seek
            source = discord.FFmpegPCMAudio(current_song['file_path'], **ffmpeg_options)
            
            # Call read() on the audio source before playing to prevent speed-up issue
            source.read()
            
            # Replace the audio source without stopping playback
            ctx.voice_client._player.source = source
            
            # Reset playback start time to current time
            music_bot.playback_start_time = time.time()
            
            # Send confirmation message
            embed = create_embed("Replay", f"[{current_song['title']}]({current_song['url']})", color=0x3498db, ctx=ctx)
            if 'thumbnail' in current_song:
                embed.set_thumbnail(url=current_song['thumbnail'])
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while replaying: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the ReplayCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(ReplayCog(bot))
