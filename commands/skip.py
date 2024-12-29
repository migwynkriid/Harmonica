import discord
from discord.ext import commands
import time
from scripts.messages import create_embed

class SkipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='skip')
    async def skip(self, ctx, amount: int = 1):
        """Skip one or multiple songs in the queue
        Usage: !skip [amount]
        amount: number of songs to skip (default: 1)"""
        from __main__ import music_bot
        
        if not music_bot or not music_bot.voice_client:
            await ctx.send(embed=create_embed("Error", "Not connected to a voice channel", color=0xe74c3c, ctx=ctx))
            return

        if not music_bot.voice_client.is_playing() and not music_bot.voice_client.is_paused():
            await ctx.send(embed=create_embed("Error", "Nothing is playing to skip", color=0xe74c3c, ctx=ctx))
            return

        if amount < 1:
            await ctx.send(embed=create_embed("Error", "Skip amount must be at least 1", color=0xe74c3c, ctx=ctx))
            return

        # Stop current song
        music_bot.voice_client.stop()
        
        # Remove additional songs from queue if requested
        if amount > 1:
            songs_to_remove = min(amount - 1, len(music_bot.queue))
            for _ in range(songs_to_remove):
                if music_bot.queue:
                    music_bot.queue.pop(0)

        music_bot.last_activity = time.time()
        if amount == 1:
            await ctx.send(embed=create_embed("Skipped", "Skipped song", color=0x3498db, ctx=ctx))
        else:
            await ctx.send(embed=create_embed("Skipped", f"Skipped {amount} songs", color=0x3498db, ctx=ctx))

async def setup(bot):
    await bot.add_cog(SkipCog(bot))
