import discord
from discord.ext import commands
import time
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import check_voice_state

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
    async def resume(self, ctx):
        """
        Resume the currently paused song.
        
        This command resumes playback of a song that was previously
        paused using the 'pause' command.
        
        Args:
            ctx: The command context
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

            # Check if the bot has a paused song that can be resumed
            if server_music_bot.voice_client and server_music_bot.voice_client.is_paused():
                server_music_bot.voice_client.resume()
                await ctx.send(embed=create_embed("Resumed", "Playback resumed", color=0x2ecc71, ctx=ctx))
            else:
                await ctx.send(embed=create_embed("Error", "Nothing is currently paused", color=0xe74c3c, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while resuming: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the ResumeCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(ResumeCog(bot))
