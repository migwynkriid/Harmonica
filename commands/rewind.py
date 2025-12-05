import discord
from discord.ext import commands
from scripts.permissions import check_dj_role
from commands.seek_base import execute_seek_command


class RewindCog(commands.Cog):
    """
    Command cog for seeking backward in the current song.
    
    This cog provides the 'rewind' command, which allows users to skip
    backward by a specified number of seconds in the currently playing song.
    """
    
    def __init__(self, bot):
        """
        Initialize the RewindCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='rewind', aliases=['rw'])
    @check_dj_role()
    async def rewind(self, ctx, seconds: int = 10):
        """
        Skip backward in the currently playing song by a specified number of seconds.
        
        This command allows users to seek backward in the currently playing song.
        The default skip amount is 10 seconds if not specified.
        This command requires DJ permissions.
        
        Usage: !rewind [seconds]
        
        Args:
            ctx: The command context
            seconds (int): Number of seconds to skip backward (default: 10)
        """
        from bot import MusicBot
        music_bot = MusicBot.get_instance(str(ctx.guild.id))
        await execute_seek_command(ctx, music_bot, seconds, "rewind")


async def setup(bot):
    """
    Setup function to add the RewindCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(RewindCog(bot))
