import discord
from discord.ext import commands
import time
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import check_voice_state

class ResumeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='resume')
    @check_dj_role()
    async def resume(self, ctx):
        """Resume the currently paused song"""
        from bot import music_bot
        
        try:
            # Check voice state
            is_valid, error_embed = await check_voice_state(ctx, music_bot)
            if not is_valid:
                await ctx.send(embed=error_embed)
                return

            if music_bot.voice_client and music_bot.voice_client.is_paused():
                music_bot.voice_client.resume()
                await ctx.send(embed=create_embed("Resumed", "Playback resumed", color=0x2ecc71, ctx=ctx))
            else:
                await ctx.send(embed=create_embed("Error", "Nothing is currently paused", color=0xe74c3c, ctx=ctx))

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while resuming: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(ResumeCog(bot))
