import discord
from discord.ext import commands
import time
from scripts.messages import create_embed

class PauseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='pause')
    async def pause(self, ctx):
        """Pause the currently playing song"""
        from __main__ import music_bot
        
        try:
            if music_bot.voice_client and music_bot.voice_client.is_playing():
                music_bot.voice_client.pause()
                music_bot.last_activity = time.time()
                await ctx.send(
                    embed=create_embed(
                        "Paused ⏸️",
                        f"[ {music_bot.current_song['title']}]({music_bot.current_song['url']})",
                        color=0xf1c40f,
                        ctx=ctx
                    )
                )
            else:
                await ctx.send(
                    embed=create_embed(
                        "Error",
                        "Nothing is playing right now.",
                        color=0xe74c3c,
                        ctx=ctx
                    )
                )
        except Exception as e:
            print(f"Error in pause command: {str(e)}")
            await ctx.send(
                embed=create_embed(
                    "Error",
                    f"Error: {str(e)}",
                    color=0xe74c3c,
                    ctx=ctx
                )
            )

async def setup(bot):
    await bot.add_cog(PauseCog(bot))
