import discord
from discord.ext import commands
from scripts.voice import leave_voice_channel
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import check_voice_state

class LeaveCog(commands.Cog):
    """
    Command cog for leaving voice channels.
    
    This cog handles the 'leave' command, which allows users to make
    the bot disconnect from the current voice channel.
    """
    
    def __init__(self, bot):
        """
        Initialize the LeaveCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self._last_member = None

    @commands.command(name='leave', aliases=['disconnect'])
    @check_dj_role()
    async def leave(self, ctx):
        """
        Leave the voice channel.
        
        This command makes the bot disconnect from the current voice channel.
        Unlike the 'stop' command, this does not clear the queue or stop
        any downloads in progress.
        
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

            # Check if bot is connected to a voice channel and disconnect if so
            if server_music_bot.voice_client and server_music_bot.voice_client.is_connected():
                await server_music_bot.voice_client.disconnect()
                await ctx.send(embed=create_embed("Left Channel", "Successfully left the voice channel", color=0x2ecc71, ctx=ctx))
            else:
                await ctx.send(embed=create_embed("Error", "I'm not connected to a voice channel", color=0xe74c3c, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while leaving: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the LeaveCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(LeaveCog(bot))
