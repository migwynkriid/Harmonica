import discord
from discord.ext import commands
from scripts.messages import create_embed

class StopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='stop')
    async def stop(self, ctx):
        """Stop playback, clear queue, and leave the voice channel"""
        from __main__ import music_bot
        
        try:
            music_bot.clear_queue()
            if music_bot.voice_client and music_bot.voice_client.is_connected():
                await music_bot.voice_client.disconnect()
            await ctx.send(embed=create_embed("Stopped", "Music stopped and queue cleared", color=0xe74c3c, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while stopping: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(StopCog(bot))