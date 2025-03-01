import discord
from discord.ext import commands
from scripts.repeatsong import repeat_song
from scripts.messages import create_embed
from scripts.permissions import check_dj_role

class Loop(commands.Cog):
    """
    Command cog for looping songs in the music queue.
    
    This cog handles the 'loop' command, which allows users to toggle
    loop mode for the currently playing song, repeating it a specified
    number of times in the queue.
    """
    
    def __init__(self, bot):
        """
        Initialize the Loop cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.looped_songs = set()  # Set to track which songs are currently looped

    async def _toggle_loop(self, ctx, count: int = 999):
        """
        Core loop functionality that can be used by both command and button.
        
        This internal method handles the actual looping logic, including
        adding the song to the queue multiple times and setting up the
        callback for future repeats.
        
        Args:
            ctx: The command context
            count (int): Number of times to add the song to the queue (default: 999)
            
        Returns:
            tuple: (bool, dict/embed) - Success status and result information
        """
        from bot import MusicBot
        music_bot = MusicBot.get_instance(ctx.guild.id)
        
        # Input validation
        if count < 1:
            return False, "Loop count must be a positive number!"
            
        # Check if there's a song playing
        if not music_bot.current_song:
            return False, "No song is currently playing!"
            
        current_song_url = music_bot.current_song['url']
        is_song_looped = current_song_url in self.looped_songs
        
        if not is_song_looped:
            # Enable looping for this song
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
                repeat_song(music_bot, ctx)  # We'll set the context later
            )
            
            return True, {
                'enabled': True,
                'song': music_bot.current_song,
                'count': count
            }
        else:
            # Disable looping for this song
            self.looped_songs.remove(current_song_url)
            
            # Clear the callback when loop is disabled
            music_bot.after_song_callback = None
            
            # Remove all songs from queue that match the current song's URL
            music_bot.queue = [song for song in music_bot.queue if song['url'] != current_song_url]
            
            return True, {
                'enabled': False,
                'song': music_bot.current_song
            }

    @commands.command(name='loop', aliases=['repeat'])
    @check_dj_role()
    async def loop(self, ctx, count: int = 999):
        """
        Toggle loop mode for the current song.
        
        This command allows users to toggle loop mode for the currently playing song.
        When enabled, the song will be added to the queue multiple times and will
        continue to be re-added after it finishes playing.
        
        Usage: !loop [count]
        count: Number of times to add the song to the queue (default: 999)
        
        Args:
            ctx: The command context
            count (int): Number of times to add the song to the queue (default: 999)
        """
        
        # Check if user is in voice chat
        if not ctx.author.voice:
            await ctx.send(embed=create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c, ctx=ctx))
            return
            
        # Check if bot is in same voice chat
        if not ctx.voice_client or ctx.author.voice.channel != ctx.voice_client.channel:
            await ctx.send(embed=create_embed("Error", "You must be in the same voice channel as the bot to use this command!", color=0xe74c3c, ctx=ctx))
            return
            
        success, result = await self._toggle_loop(ctx, count)
        
        if not success:
            await ctx.send(embed=create_embed("Error", result, color=0xe74c3c, ctx=ctx))
            return

        color = 0x3498db if result['enabled'] else 0xe74c3c
        title = "Looping enabled :repeat: " if result['enabled'] else "Looping disabled :repeat: "
        description = f"[{result['song']['title']}]({result['song']['url']})"

        embed = create_embed(
            title,
            description,
            color=color,
            thumbnail_url=result['song'].get('thumbnail'),
            ctx=ctx
        )
        await ctx.send(embed=embed)

async def setup(bot):
    """
    Setup function to add the Loop cog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(Loop(bot))
