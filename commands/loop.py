import discord
from discord.ext import commands
from scripts.repeatsong import repeat_song

class Loop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop_enabled = False

    @commands.command()
    async def loop(self, ctx):
        """Toggle loop mode for the current song"""
        from __main__ import music_bot
        
        self.loop_enabled = not self.loop_enabled
        status = "enabled" if self.loop_enabled else "disabled"
        
        if self.loop_enabled and music_bot.current_song:
            # Immediately add current song to queue
            music_bot.queue.append(music_bot.current_song)
            # Set up callback for future repeats
            music_bot.after_song_callback = lambda: self.bot.loop.create_task(
                repeat_song(music_bot, ctx)
            )
        else:
            # Clear the callback when loop is disabled
            music_bot.after_song_callback = None
        
        embed = discord.Embed(
            title="Loop Mode",
            description=f"Loop mode {status}",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Loop(bot))
