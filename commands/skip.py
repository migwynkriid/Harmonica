import discord
from discord.ext import commands
import time
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import check_voice_state

class SkipCog(commands.Cog):
    """
    Command cog for skipping songs in the music queue.
    
    This cog handles the 'skip' command, which allows users to skip
    the currently playing song and optionally multiple songs in the queue.
    """
    
    def __init__(self, bot):
        """
        Initialize the SkipCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self._last_member = None

    async def _skip_song(self, amount: int = 1, ctx=None):
        """
        Core skip functionality that can be used by both command and button.
        
        This internal method handles the actual skipping logic, including
        handling looped songs and removing multiple songs from the queue.
        
        Args:
            amount (int): Number of songs to skip (default: 1)
            ctx: The command context
            
        Returns:
            tuple: (bool, str/dict) - Success status and result message or song info
        """
        from bot import MusicBot
        
        # Get server-specific music bot instance
        guild_id = ctx.guild.id if ctx else None
        if not guild_id:
            return False, "Invalid guild context"
            
        server_music_bot = MusicBot.get_instance(str(guild_id))
        
        if not server_music_bot or not server_music_bot.voice_client:
            return False, "Not connected to a voice channel"

        if not server_music_bot.voice_client.is_playing() and not server_music_bot.voice_client.is_paused():
            return False, "Nothing is playing to skip"

        if amount < 1:
            return False, "Skip amount must be at least 1"

        # Store current song info before skipping
        current_song = server_music_bot.current_song
        
        # Set the skipped flag to indicate this was a manual skip
        # This affects how the after_playing callback behaves
        server_music_bot.was_skipped = True
        
        # Check if current song is looping
        loop_cog = self.bot.get_cog('Loop')
        is_looping = loop_cog and current_song and current_song['url'] in loop_cog.looped_songs
        
        # If song is looping, remove it from looped songs and clear its instances from queue
        if is_looping:
            loop_cog.looped_songs.remove(current_song['url'])
            # Remove all instances of the looped song from the queue
            server_music_bot.queue = [song for song in server_music_bot.queue if song['url'] != current_song['url']]
            server_music_bot.after_song_callback = None
        
        # Stop current song - this will trigger the after_playing callback
        server_music_bot.voice_client.stop()
        
        # Remove additional songs from queue if requested
        if amount > 1:
            songs_to_remove = min(amount - 1, len(server_music_bot.queue))
            if songs_to_remove > 0:
                del server_music_bot.queue[:songs_to_remove]
                return True, f"Skipped current song and {songs_to_remove} songs from queue"
        
        # Update last activity timestamp
        server_music_bot.last_activity = time.time()
        return True, current_song if current_song else "Skipped"

    @commands.command(name='skip')
    @check_dj_role()
    async def skip(self, ctx, amount: int = 1):
        """
        Skip one or multiple songs in the queue.
        
        This command allows users to skip the currently playing song
        and optionally multiple songs in the queue.
        
        Usage: !skip [amount]
        amount: number of songs to skip (default: 1)
        
        Args:
            ctx: The command context
            amount (int): Number of songs to skip (default: 1)
        """
        from bot import MusicBot
        
        try:
            # Get server-specific music bot instance
            server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
            
            # Check voice state (user must be in same voice channel as bot)
            is_valid, error_embed = await check_voice_state(ctx, server_music_bot)
            if not is_valid:
                await ctx.send(embed=error_embed)
                return

            # Call the internal skip method
            success, result = await self._skip_song(amount, ctx)
            
            if not success:
                await ctx.send(embed=create_embed("Error", result, color=0xe74c3c, ctx=ctx))
                return

            # Store ctx in current_song for footer information
            if isinstance(result, dict):
                result['ctx'] = ctx

            # Don't send a skip message here since it's handled by the after_playing callback
            # Only show message for multiple skips
            if isinstance(result, dict) and amount > 1:
                await ctx.send(embed=create_embed("Skipped", f"Skipped current song and {amount - 1} songs from queue", color=0x3498db, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while skipping: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the SkipCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(SkipCog(bot))
