import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.config import FFMPEG_OPTIONS
from scripts.activity import update_activity
from scripts.voice_checks import check_voice_state

class ReplayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='replay')
    @check_dj_role()
    async def replay(self, ctx):
        """Restart the currently playing song"""
        from bot import music_bot
        
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

            # Stop current playback
            ctx.voice_client.stop()
            
            # Store current song info and ensure it stays as current song
            current_song = music_bot.current_song
            music_bot.current_song = current_song  # Reassign to ensure it's maintained
            
            # If this is the last song, add it back to queue to prevent queue from appearing empty
            if len(music_bot.queue) == 0:
                music_bot.queue.append(current_song)
            
            # Reset playback start time and set status
            music_bot.playback_start_time = None
            music_bot.is_playing = True
            
            # Create a new FFmpeg audio source with the same file
            source = discord.FFmpegOpusAudio(current_song['file_path'], **FFMPEG_OPTIONS)
            
            # Call read() on the audio source before playing to prevent speed-up issue
            source.read()
            
            # Play the audio
            ctx.voice_client.play(source, after=lambda e: music_bot.bot_loop.create_task(music_bot.after_playing_coro(e, ctx)))
            
            # Update bot activity using the bot instance
            await self.bot.change_presence(activity=discord.Game(name=f" {current_song['title']}"))
            
            embed = create_embed("Replay", f" Restarted: {current_song['title']}", color=0x3498db, ctx=ctx)
            if 'thumbnail' in current_song:
                embed.set_thumbnail(url=current_song['thumbnail'])
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while replaying: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(ReplayCog(bot))
