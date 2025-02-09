import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.clear_queue import clear_queue
from scripts.voice_checks import check_voice_state
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

            # Cancel any active downloads first
            await music_bot.cancel_downloads()
            
            # Stop any current playback
            if music_bot.voice_client and music_bot.voice_client.is_playing():
                music_bot.voice_client.stop()
            
            # Clean up all queued messages with 1-second delay between each
            for message in list(music_bot.queued_messages.values()):
                try:
                    await message.delete()
                    await asyncio.sleep(0.1)  # Add 1-second delay between deletions
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
            
            await ctx.send(embed=create_embed("Stopped", "Playback stopped and cleared the queue", color=0xe74c3c, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while stopping: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(StopCog(bot))