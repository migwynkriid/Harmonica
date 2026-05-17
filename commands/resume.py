from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import requires_voice
from scripts.constants import EMBED_COLOR_ERROR, EMBED_COLOR_SUCCESS

class ResumeCog(commands.Cog):
    """
    Command cog for resuming music playback.
    
    This cog handles the 'resume' command, which allows users to resume
    a paused song in a voice channel.
    """
    
    def __init__(self, bot):
        """
        Initialize the ResumeCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='resume')
    @check_dj_role()
    @requires_voice()
    async def resume(self, ctx, music_bot):
        """
        Resume the currently paused song.
        
        This command resumes playback of a song that was previously
        paused using the 'pause' command.
        
        Args:
            ctx: The command context
            music_bot: The MusicBot instance (injected by @requires_voice)
        """
        try:
            # Check if the bot has a paused song that can be resumed
            if music_bot.voice_client and music_bot.voice_client.is_paused():
                music_bot.voice_client.resume()
                await ctx.send(embed=create_embed("Resumed", "Playback resumed", color=EMBED_COLOR_SUCCESS, ctx=ctx))
            else:
                await ctx.send(embed=create_embed("Error", "Nothing is currently paused", color=EMBED_COLOR_ERROR, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while resuming: {str(e)}", color=EMBED_COLOR_ERROR, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the ResumeCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(ResumeCog(bot))
