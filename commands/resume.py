import discord
from discord.ext import commands
import time
from scripts.messages import create_embed
from scripts.permissions import check_dj_role

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
            if music_bot.voice_client and music_bot.voice_client.is_paused():
                music_bot.voice_client.resume()
                music_bot.last_activity = time.time()
                await ctx.send(
                    embed=create_embed(
                        "Resumed ▶️",
                        f"[ {music_bot.current_song['title']}]({music_bot.current_song['url']})",
                        color=0x2ecc71,
                        ctx=ctx
                    )
                )
            else:
                await ctx.send(
                    embed=create_embed(
                        "Error",
                        "Nothing is paused right now.",
                        color=0xe74c3c,
                        ctx=ctx
                    )
                )
        except Exception as e:
            print(f"Error in resume command: {str(e)}")
            await ctx.send(
                embed=create_embed(
                    "Error",
                    f"Error: {str(e)}",
                    color=0xe74c3c,
                    ctx=ctx
                )
            )

async def setup(bot):
    await bot.add_cog(ResumeCog(bot))
