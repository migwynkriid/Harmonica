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
        from bot import music_bot
        
        try:
            # Check voice state
            is_valid, error_embed = await check_voice_state(ctx, music_bot)
            if not is_valid:
                await ctx.send(embed=error_embed)
                return

            # Stop cache checking immediately
            playlist_cache.stop_cache_check()

            # Update now playing message if it exists
            if music_bot.now_playing_message and music_bot.current_song:
                try:
                    finished_embed = create_embed(
                        "Finished playing",
                        f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})",
                        color=0x808080,
                        thumbnail_url=music_bot.current_song.get('thumbnail'),
                        ctx=ctx
                    )
                    await music_bot.now_playing_message.edit(embed=finished_embed, view=None)
                except Exception as e:
                    print(f"Error updating now playing message: {str(e)}")
            
            # Cancel any active downloads first
            await music_bot.cancel_downloads()
            
            # Stop any current playback
            if music_bot.voice_client and music_bot.voice_client.is_playing():
                music_bot.voice_client.stop()
            
            # Clean up all queued messages with 1-second delay between each
            for message in list(music_bot.queued_messages.values()):
                try:
                    await message.delete()
                    await asyncio.sleep(0.1)  # Add 0.1-second delay between deletions
                except:
                    pass  # Message might already be deleted
            music_bot.queued_messages.clear()
            
            # Clear the queue and disconnect
            clear_queue()
            if music_bot.voice_client and music_bot.voice_client.is_connected():
                await music_bot.voice_client.disconnect()
                
            # Reset the music bot state
            music_bot.current_song = None
            music_bot.is_playing = False
            
            # Clear any remaining downloads from queue
            while not music_bot.download_queue.empty():
                try:
                    music_bot.download_queue.get_nowait()
                    music_bot.download_queue.task_done()
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