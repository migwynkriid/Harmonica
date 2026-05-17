from discord.ext import commands
from scripts.shufflelogic import shuffle_queue
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import check_voice_state
from scripts.constants import EMBED_COLOR_ERROR, EMBED_COLOR_SUCCESS


class ShuffleCog(commands.Cog):
    """
    Command cog for shuffling the music queue.
    
    This cog handles the 'shuffle' command, which allows users to
    randomly reorder the songs in the queue.
    """
    
    def __init__(self, bot):
        """
        Initialize the ShuffleCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='shuffle')
    @check_dj_role()
    async def shuffle(self, ctx):
        """
        Randomly shuffle all songs in the queue.
        
        This command randomly reorders all songs in the queue, except for
        the currently playing song and any songs that are still being downloaded.
        
        Args:
            ctx: The command context
        """
        from bot import MusicBot
        
        # Get server-specific music bot instance
        server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
        
        # Check voice state
        is_valid, error_embed = await check_voice_state(ctx, server_music_bot)
        if not is_valid:
            await ctx.send(embed=error_embed)
            return
            
        # Call the shuffle_queue function from shufflelogic.py to perform the actual shuffling
        success = await shuffle_queue(ctx, server_music_bot)
        
        if success:
            await ctx.send(embed=create_embed("Queue Shuffled", "The queue has been randomly shuffled!\n Pending downloads are not shuffled", color=EMBED_COLOR_SUCCESS, ctx=ctx))
        else:
            await ctx.send(embed=create_embed("Cannot Shuffle", "Nothing is playing or nothing is waiting in the queue!", color=EMBED_COLOR_ERROR, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the ShuffleCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(ShuffleCog(bot))
