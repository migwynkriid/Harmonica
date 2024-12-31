import discord
from discord.ext import commands
from scripts.repeatsong import repeat_song
from scripts.messages import create_embed

class Loop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.looped_songs = set()

    @commands.command(aliases=['repeat'])
    async def loop(self, ctx, count: int = 999):
        """Toggle loop mode for the current song. Optionally specify number of times to add the song."""
        from __main__ import music_bot
        
        # Input validation
        if count < 1:
            await ctx.send("Loop count must be a positive number!")
            return
            
        if not music_bot.current_song:
            await ctx.send("No song is currently playing!")
            return

        current_song_url = music_bot.current_song['url']
        is_song_looped = current_song_url in self.looped_songs
        
        if not is_song_looped:
            self.looped_songs.add(current_song_url)
            # Find the position of the current song in the queue (if it exists)
            current_song_position = -1
            for i, song in enumerate(music_bot.queue):
                if song['url'] == current_song_url:
                    current_song_position = i
                    break
            
            # If current song is not in queue, position will be at start
            insert_position = current_song_position + 1 if current_song_position != -1 else 0
            
            # Insert the looped song right after the current position
            for _ in range(count):
                music_bot.queue.insert(insert_position, music_bot.current_song)
                insert_position += 1  # Increment position for next insertion
            
            # Set up callback for future repeats
            music_bot.after_song_callback = lambda: self.bot.loop.create_task(
                repeat_song(music_bot, ctx)
            )
            
            # Create description based on whether count was explicitly provided
            count_was_provided = len(ctx.message.content.split()) > 1
            title = f"Looping enabled :repeat: "
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
            # Remove song from looped songs set
            self.looped_songs.remove(current_song_url)
            
            # Clear the callback when loop is disabled
            music_bot.after_song_callback = None
            
            # Remove all songs from queue that match the current song's URL
            music_bot.queue = [song for song in music_bot.queue if song['url'] != current_song_url]
            
            description = f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})"
            
            embed = create_embed(
                "Looping disabled :repeat: ",
                description,
                color=0xe74c3c,
                thumbnail_url=music_bot.current_song.get('thumbnail'),
                ctx=ctx
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Loop(bot))
