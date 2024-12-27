import discord
from discord.ext import commands

class MaxCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='max')
    async def max(self, ctx):
        """Simulate !play with RadioMax URL"""
        from __main__ import music_bot, play
        
        try:
            await play(ctx, query='https://azuracast.novi-net.net/radio/8010/radiomax.aac')
        except Exception as e:
            await ctx.send(embed=music_bot.create_embed("Error", f"An error occurred while executing !max: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(MaxCog(bot))