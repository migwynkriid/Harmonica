import discord
from discord.ext import commands
import sys
import os
from scripts.messages import create_embed

# Add the parent directory to sys.path to allow importing from bot
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

class NowPlayingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='nowplaying', aliases=['np'])
    async def nowplaying(self, ctx):
        """Show the currently playing song"""
        # Access the music_bot from the global scope
        from __main__ import music_bot
        
        if not music_bot:
            await ctx.send("Music bot is not initialized yet. Please wait a moment and try again.")
            return

        if not music_bot.current_song:
            await ctx.send(embed=create_embed("Error", "No song is currently playing!", color=0xe74c3c, ctx=ctx))
            return

        embed = create_embed(
            "Now Playing 🎵",
            f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})",
            color=0x3498db,
            thumbnail_url=music_bot.current_song.get('thumbnail'),
            ctx=ctx
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(NowPlayingCog(bot))