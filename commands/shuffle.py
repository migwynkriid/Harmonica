from discord.ext import commands
from scripts.shufflelogic import shuffle_queue
from scripts.ui_components import create_embed

class ShuffleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='shuffle')
    async def shuffle(self, ctx):
        """Randomly shuffle all songs in the queue"""
        from bot import music_bot
        success = await shuffle_queue(ctx, music_bot)
        
        if success:
            await ctx.send(embed=create_embed("Queue Shuffled", "The queue has been randomly shuffled!", color=0x2ecc71, ctx=ctx))
        else:
            await ctx.send(embed=create_embed("Cannot Shuffle", "The queue is empty!", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(ShuffleCog(bot))
