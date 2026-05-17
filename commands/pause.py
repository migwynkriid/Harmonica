from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import requires_voice
from scripts.constants import EMBED_COLOR_ERROR, EMBED_COLOR_SUCCESS, ERROR_NOTHING_PLAYING

class PauseCog(commands.Cog):
    """
    Command cog for pausing music playback.
    
    This cog handles the 'pause' command, which allows users to pause
    the currently playing song in a voice channel.
    """
    
    def __init__(self, bot):
        """
        Initialize the PauseCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='pause')
    @check_dj_role()
    @requires_voice()
    async def pause(self, ctx, music_bot):
        """
        Pause the currently playing song.
        
        This command pauses the currently playing song in the voice channel.
        The song can be resumed using the 'resume' command.
        
        Args:
            ctx: The command context
            music_bot: The MusicBot instance (injected by @requires_voice)
        """
        try:
            # Check if the bot is playing something that can be paused
            if music_bot.voice_client and music_bot.voice_client.is_playing():
                music_bot.voice_client.pause()
                await ctx.send(embed=create_embed("Paused", "Playback paused", color=EMBED_COLOR_SUCCESS, ctx=ctx))
            else:
                await ctx.send(embed=create_embed("Error", ERROR_NOTHING_PLAYING, color=EMBED_COLOR_ERROR, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while pausing: {str(e)}", color=EMBED_COLOR_ERROR, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the PauseCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(PauseCog(bot))
