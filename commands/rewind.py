import discord
from discord.ext import commands
from scripts.permissions import check_dj_role
from scripts.config import load_config
from commands._seek_base import execute_seek_command


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
        config = load_config()
        self.default_rewind = config.get('SEEK', {}).get('DEFAULT_REWIND', 10)

    @commands.command(name='rewind', aliases=['rw'])
    @check_dj_role()
    async def rewind(self, ctx, seconds: int = None):
        """
        Skip backward in the currently playing song by a specified number of seconds.
        
        This command allows users to seek backward in the currently playing song.
        The default skip amount is configurable via config.json.
        This command requires DJ permissions.
        
        Usage: !rewind [seconds]
        
        Args:
            ctx: The command context
            seconds (int): Number of seconds to skip backward (default from config)
        """
        if seconds is None:
            seconds = self.default_rewind
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
