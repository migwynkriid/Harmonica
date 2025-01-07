import discord
from discord.ext import commands
from scripts.queueclear import clear_queue_command

class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='clear', aliases=['clearqueue'])
    async def clear(self, ctx):
        """Clears all songs from the queue"""
        from bot import music_bot
        await clear_queue_command(ctx, music_bot)

async def setup(bot):
    await bot.add_cog(Clear(bot))
