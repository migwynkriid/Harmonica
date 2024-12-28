import discord
from discord.ext import commands
from scripts.voice import leave_voice_channel
from scripts.messages import create_embed

class LeaveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='leave')
    async def leave(self, ctx):
        """Leave the voice channel"""
        from __main__ import music_bot
        
        if music_bot and music_bot.voice_client and music_bot.voice_client.is_connected():
            await leave_voice_channel(music_bot)
            await ctx.send(embed=create_embed("Left Channel", "Disconnected from voice channel", color=0x3498db, ctx=ctx))
        else:
            await ctx.send(embed=create_embed("Error", "I'm not in a voice channel", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(LeaveCog(bot))
