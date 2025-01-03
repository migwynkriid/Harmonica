import discord
from discord.ext import commands
import time
from scripts.messages import create_embed

class SkipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    async def _skip_song(self, amount: int = 1, ctx=None):
        """Core skip functionality that can be used by both command and button"""
        from __main__ import music_bot
        
        if not music_bot or not music_bot.voice_client:
            return False, "Not connected to a voice channel"

        if not music_bot.voice_client.is_playing() and not music_bot.voice_client.is_paused():
            return False, "Nothing is playing to skip"

        if amount < 1:
            return False, "Skip amount must be at least 1"

        # Store current song info before skipping
        current_song = music_bot.current_song
        
        # Set the skipped flag
        music_bot.was_skipped = True
        
        # Check if current song is looping
        loop_cog = self.bot.get_cog('Loop')
        is_looping = loop_cog and current_song and current_song['url'] in loop_cog.looped_songs
        
        # If song is looping, remove it from looped songs and clear its instances from queue
        if is_looping:
            loop_cog.looped_songs.remove(current_song['url'])
            music_bot.queue = [song for song in music_bot.queue if song['url'] != current_song['url']]
            music_bot.after_song_callback = None
        
        # Stop current song
        music_bot.voice_client.stop()
        
        # Remove additional songs from queue if requested
        if amount > 1:
            songs_to_remove = min(amount - 1, len(music_bot.queue))
            if songs_to_remove > 0:
                del music_bot.queue[:songs_to_remove]
                return True, f"Skipped current song and {songs_to_remove} songs from queue"
        
        music_bot.last_activity = time.time()
        return True, current_song if current_song else "Skipped"

    @commands.command(name='skip')
    async def skip(self, ctx, amount: int = 1):
        """Skip one or multiple songs in the queue
        Usage: !skip [amount]
        amount: number of songs to skip (default: 1)"""
        success, result = await self._skip_song(amount, ctx)
        
        if not success:
            await ctx.send(embed=create_embed("Error", result, color=0xe74c3c, ctx=ctx))
            return

        # Store ctx in current_song for footer information
        if isinstance(result, dict):
            result['ctx'] = ctx

        # Don't send a skip message here since it's handled by the after_playing callback
        if isinstance(result, dict) and amount > 1:  # Only show message for multiple skips
            await ctx.send(embed=create_embed("Skipped", f"Skipped current song and {amount - 1} songs from queue", color=0x3498db, ctx=ctx))

async def setup(bot):
    await bot.add_cog(SkipCog(bot))
