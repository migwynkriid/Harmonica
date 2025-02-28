import discord
from discord.ext import commands
import time
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import check_voice_state

class PauseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='pause')
    @check_dj_role()
    async def pause(self, ctx):
        """Pause the currently playing song"""
        from bot import MusicBot
        
        try:
            # Get server-specific music bot instance
            server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
            
            # Check voice state
            is_valid, error_embed = await check_voice_state(ctx, server_music_bot)
            if not is_valid:
                await ctx.send(embed=error_embed)
                return

            if server_music_bot.voice_client and server_music_bot.voice_client.is_playing():
                server_music_bot.voice_client.pause()
                await ctx.send(embed=create_embed("Paused", "Playback paused", color=0x2ecc71, ctx=ctx))
            else:
                await ctx.send(embed=create_embed("Error", "Nothing is currently playing", color=0xe74c3c, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while pausing: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(PauseCog(bot))
