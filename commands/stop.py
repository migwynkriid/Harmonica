import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.clear_queue import clear_queue
from scripts.voice_checks import check_voice_state
from scripts.caching import playlist_cache
import asyncio

class StopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='stop')
    @check_dj_role()
    async def stop(self, ctx):
        """Stop playback, clear queue, and leave the voice channel"""
        from bot import MusicBot
        
        try:
            # Get server-specific music bot instance
            server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
            
            # Check voice state
            is_valid, error_embed = await check_voice_state(ctx, server_music_bot)
            if not is_valid:
                await ctx.send(embed=error_embed)
                return

            # Stop cache checking immediately
            playlist_cache.stop_cache_check()

            # Update now playing message if it exists
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
                    print(f"Error updating now playing message: {str(e)}")
            
            # Cancel any active downloads first
            await server_music_bot.cancel_downloads()
            
            # Stop any current playback
            if server_music_bot.voice_client and server_music_bot.voice_client.is_playing():
                server_music_bot.voice_client.stop()
            
            # Clean up all queued messages with 1-second delay between each
            for message in list(server_music_bot.queued_messages.values()):
                try:
                    await message.delete()
                    await asyncio.sleep(0.1)  # Add 0.1-second delay between deletions
                except:
                    pass  # Message might already be deleted
            server_music_bot.queued_messages.clear()
            
            # Clear the queue and disconnect
            clear_queue(ctx.guild.id)
            if server_music_bot.voice_client and server_music_bot.voice_client.is_connected():
                await server_music_bot.voice_client.disconnect()
                
            # Reset the music bot state
            server_music_bot.current_song = None
            server_music_bot.is_playing = False
            
            # Clear any remaining downloads from queue
            while not server_music_bot.download_queue.empty():
                try:
                    server_music_bot.download_queue.get_nowait()
                    server_music_bot.download_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            
            await ctx.send(embed=create_embed("Stopped", "Playback stopped and cleared the queue", color=0xe74c3c, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while stopping: {str(e)}", color=0xe74c3c, ctx=ctx))
        finally:
            # Resume cache checking for future commands
            playlist_cache.resume_cache_check()

async def setup(bot):
    await bot.add_cog(StopCog(bot))