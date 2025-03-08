import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.clear_queue import clear_queue
from scripts.voice_checks import check_voice_state
from scripts.caching import playlist_cache
from scripts.activity import update_activity
import asyncio

class StopCog(commands.Cog):
    """
    Command cog for stopping music playback completely.
    
    This cog handles the 'stop' command, which stops the current playback,
    clears the queue, and disconnects the bot from the voice channel.
    """
    
    def __init__(self, bot):
        """
        Initialize the StopCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self._last_member = None

    @commands.command(name='stop')
    @check_dj_role()
    async def stop(self, ctx):
        """
        Stop playback, clear queue, and leave the voice channel.
        
        This command performs a complete shutdown of the music playback:
        1. Stops any currently playing song
        2. Cancels any active downloads
        3. Clears the queue
        4. Removes all queued messages
        5. Disconnects from the voice channel
        6. Clears the bot's activity status
        
        Args:
            ctx: The command context
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

            # Stop cache checking immediately to prevent new cache operations
            playlist_cache.stop_cache_check()

            # Update now playing message if it exists to show it's finished
            if server_music_bot.now_playing_message and server_music_bot.current_song:
                try:
                    finished_embed = create_embed(
                        "Finished playing",
                        f"[{server_music_bot.current_song['title']}]({server_music_bot.current_song['url']})",
                        color=0x808080,
                        thumbnail_url=server_music_bot.current_song.get('thumbnail'),
                        ctx=ctx
                    )
                    await server_music_bot.now_playing_message.edit(embed=finished_embed, view=None)
                except Exception as e:
                    # Silently handle errors updating now playing message
                    pass
            
            # Cancel any active downloads first to prevent new songs from being added
            try:
                await server_music_bot.cancel_downloads(disconnect_voice=False)  # Don't disconnect yet
            except Exception as e:
                # Silently handle errors canceling downloads
                pass
            
            # Stop any current playback
            try:
                if server_music_bot.voice_client and server_music_bot.voice_client.is_playing():
                    server_music_bot.voice_client.stop()
            except Exception as e:
                # Silently handle errors stopping playback
                pass
            
            # Clean up all queued messages with small delay between each to avoid rate limiting
            for message in list(server_music_bot.queued_messages.values()):
                try:
                    await message.delete()
                    await asyncio.sleep(0.1)  # Add 0.1-second delay between deletions
                except:
                    pass  # Message might already be deleted
            server_music_bot.queued_messages.clear()
            
            # Clear the queue
            clear_queue(ctx.guild.id)
            
            # Disconnect from voice channel
            try:
                if server_music_bot.voice_client and server_music_bot.voice_client.is_connected():
                    await server_music_bot.voice_client.disconnect(force=True)
            except Exception as e:
                # Silently handle errors disconnecting
                pass
                
            # Reset the music bot state
            server_music_bot.voice_client = None  # Explicitly set to None to prevent further errors
            server_music_bot.current_song = None
            server_music_bot.is_playing = False
            # Add a flag to indicate the bot has been explicitly stopped
            server_music_bot.explicitly_stopped = True
            
            # Clear any remaining downloads from queue to prevent them from being processed
            while not server_music_bot.download_queue.empty():
                try:
                    server_music_bot.download_queue.get_nowait()
                    server_music_bot.download_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            
            # Update the bot's activity status to clear the "Playing song" status
            await update_activity(self.bot, current_song=None, is_playing=False)
            
            await ctx.send(embed=create_embed("Stopped", "Playback stopped and cleared the queue", color=0xe74c3c, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while stopping: {str(e)}", color=0xe74c3c, ctx=ctx))
        finally:
            # Resume cache checking for future commands
            playlist_cache.resume_cache_check()

async def setup(bot):
    """
    Setup function to add the StopCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(StopCog(bot))