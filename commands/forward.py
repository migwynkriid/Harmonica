import discord
from discord.ext import commands
from scripts.permissions import check_dj_role
from commands._seek_base import execute_seek_command


class ForwardCog(commands.Cog):
    """
    Command cog for seeking forward in the current song.
    
    This cog provides the 'forward' command, which allows users to skip
    forward by a specified number of seconds in the currently playing song.
    """
    
    def __init__(self, bot):
        """
        Initialize the ForwardCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='forward', aliases=['ff', 'fastforward', 'fw'])
    @check_dj_role()
    async def forward(self, ctx, seconds: int = 10):
        """
        Skip forward in the currently playing song by a specified number of seconds.
        
        This command allows users to seek forward in the currently playing song.
        The default skip amount is 10 seconds if not specified.
        This command requires DJ permissions.
        
        Usage: !forward [seconds]
        
        Args:
            ctx: The command context
            seconds (int): Number of seconds to skip forward (default: 10)
        """
        from bot import MusicBot
        music_bot = MusicBot.get_instance(str(ctx.guild.id))
        await execute_seek_command(ctx, music_bot, seconds, "forward")


async def setup(bot):
    """
    Setup function to add the ForwardCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(ForwardCog(bot))
