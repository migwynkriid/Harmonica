import discord
from discord.ext import commands
from scripts.messages import create_embed

class MaxCog(commands.Cog):
    """
    Command cog for playing Radio Max stream.
    
    This cog provides a command to play the Radio Max online radio stream.
    """
    
    def __init__(self, bot):
        """
        Initialize the MaxCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self._last_member = None

    @commands.command(name='max')
    async def max(self, ctx):
        """
        Play Radio Max stream.
        
        This command plays the Radio Max online radio stream by calling
        the play command with the Radio Max stream URL. This provides
        a convenient shortcut for users to access this specific stream.
        
        Args:
            ctx: The command context
        """
        from bot import MusicBot
        music_bot = MusicBot.get_instance(ctx.guild.id)
        
        try:
            play_cog = self.bot.get_cog('PlayCog')
            if play_cog:
                await play_cog.play(ctx, query='https://azuracast.novi-net.net/radio/8010/radiomax.aac')
            else:
                await ctx.send(embed=create_embed(
                    "Error",
                    "Could not find the play command. Please make sure the bot is properly set up.",
                    color=0xe74c3c,
                    ctx=ctx
                ))
        except Exception as e:
            await ctx.send(embed=create_embed(
                "Error", 
                f"An error occurred while playing Radio Max: {str(e)}", 
                color=0xe74c3c, 
                ctx=ctx
            ))

async def setup(bot):
    """
    Setup function to add the MaxCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(MaxCog(bot))
