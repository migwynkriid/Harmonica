import discord
from discord.ext import commands
import time
from scripts.messages import create_embed

class SkipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='skip')
    async def skip(self, ctx):
        """Skip the current song"""
        from __main__ import music_bot
        
        if music_bot and music_bot.voice_client and (music_bot.voice_client.is_playing() or music_bot.voice_client.is_paused()):
            music_bot.voice_client.stop()
            music_bot.last_activity = time.time()
            await ctx.send(embed=create_embed("Skipped", "Skipped the current song", color=0x3498db, ctx=ctx))
        else:
            await ctx.send(embed=create_embed("Error", "Nothing is playing to skip", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(SkipCog(bot))
