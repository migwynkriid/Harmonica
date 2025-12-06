import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.queueclear import clear_queue_command
from scripts.voice_checks import check_voice_state

class ClearCog(commands.Cog):
    """
    Command cog for clearing the music queue.
    
    This cog handles the 'clear' command, which allows users to clear
    the entire queue or remove a specific song from the queue.
    """
    
    def __init__(self, bot):
        """
        Initialize the ClearCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='clear', aliases=['clearqueue'])
    @check_dj_role()
    async def clear(self, ctx, position: int = None):
        """
        Clear the queue or remove a specific song.
        
        This command allows users to either clear the entire queue (if no position
        is specified) or remove a specific song from the queue by its position.
        
        Args:
            ctx: The command context
            position (int, optional): The position of the song to remove from the queue.
                                     If not provided, the entire queue will be cleared.
        """
        from bot import MusicBot

        try:
            # Get server-specific music bot instance
            server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
            
            # Check voice state (user must be in same voice channel as bot)
            is_valid, error_embed = await check_voice_state(ctx, server_music_bot)
            if not is_valid:
                await ctx.send(embed=error_embed)
                return

            # Call the clear queue command function from queueclear.py
            await clear_queue_command(ctx, server_music_bot, position)

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while clearing: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the ClearCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(ClearCog(bot))
