from discord.ext import commands
from scripts.shufflelogic import shuffle_queue
from scripts.messages import create_embed
from scripts.permissions import check_dj_role

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
        
        # Check if user is in voice chat
        if not ctx.author.voice:
            await ctx.send(embed=create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c, ctx=ctx))
            return
            
        # Check if bot is in same voice chat
        if not ctx.voice_client or ctx.author.voice.channel != ctx.voice_client.channel:
            await ctx.send(embed=create_embed("Error", "You must be in the same voice channel as the bot to use this command!", color=0xe74c3c, ctx=ctx))
            return
            
        # Call the shuffle_queue function from shufflelogic.py to perform the actual shuffling
        success = await shuffle_queue(ctx, server_music_bot)
        
        if success:
            await ctx.send(embed=create_embed("Queue Shuffled", "The queue has been randomly shuffled!\n Pending downloads are not shuffled", color=0x2ecc71, ctx=ctx))
        else:
            await ctx.send(embed=create_embed("Cannot Shuffle", "Nothing is playing or nothing is waiting in the queue!", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the ShuffleCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(ShuffleCog(bot))
