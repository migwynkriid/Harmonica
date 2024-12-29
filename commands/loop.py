import discord
from discord.ext import commands
from scripts.repeatsong import repeat_song
from scripts.messages import create_embed

class Loop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop_enabled = False

    @commands.command()
    async def loop(self, ctx, count: int = 100):
        """Toggle loop mode for the current song. Optionally specify number of times to add the song."""
        from __main__ import music_bot
        
        # Input validation
        if count < 1:
            await ctx.send("Loop count must be a positive number!")
            return
            
        self.loop_enabled = not self.loop_enabled
        
        if self.loop_enabled and music_bot.current_song:
            # Add current song to queue the specified number of times
            for _ in range(count):
                music_bot.queue.append(music_bot.current_song)
            # Set up callback for future repeats
            music_bot.after_song_callback = lambda: self.bot.loop.create_task(
                repeat_song(music_bot, ctx)
            )
            
            # Create description based on whether count was explicitly provided
            count_was_provided = len(ctx.message.content.split()) > 1
            title = f"Loop enabled 🔁"
            description = f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})"
            if count_was_provided:
                description += f"\nWill be added {count} time{'s' if count > 1 else ''}"
                
            embed = create_embed(
                title,
                description,
                color=0x3498db,
                thumbnail_url=music_bot.current_song.get('thumbnail'),
                ctx=ctx
            )
        else:
            # Clear the callback when loop is disabled
            music_bot.after_song_callback = None
            
            if music_bot.current_song:
                # Remove all songs from queue that match the current song's URL
                original_length = len(music_bot.queue)
                music_bot.queue = [song for song in music_bot.queue if song['url'] != music_bot.current_song['url']]
                
                description = f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})"
            else:
                description = "No song is currently playing"
                
            embed = create_embed(
                "Loop Mode Disabled 🔁",
                description,
                color=0xe74c3c,
                ctx=ctx
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Loop(bot))
