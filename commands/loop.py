import discord
from discord.ext import commands

class LoopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='loop', aliases=['repeat'])
    async def loop(self, ctx):
        """Toggle loop mode for the current song"""
        from __main__ import music_bot
        
        if not music_bot.current_song:
            await ctx.send(embed=music_bot.create_embed("Error", "No song is currently playing!", color=0xe74c3c, ctx=ctx))
            return
            
        music_bot.loop_mode = not music_bot.loop_mode
        status = "enabled" if music_bot.loop_mode else "disabled"
        color = 0x2ecc71 if music_bot.loop_mode else 0xe74c3c
        
        await ctx.send(embed=music_bot.create_embed(
            f"Loop Mode {status.title()}", 
            f"[🎵 {music_bot.current_song['title']}]({music_bot.current_song['url']}) will {'now' if music_bot.loop_mode else 'no longer'} be looped", 
            color=color, 
            ctx=ctx
        ))

async def setup(bot):
    await bot.add_cog(LoopCog(bot))
