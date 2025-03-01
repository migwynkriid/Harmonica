import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
import asyncio

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
        Toggle loop for the current song.
        
        Args:
            ctx: The command context
            count (int): Number of times to add the song to the queue (default: 999)
            
        Returns:
            tuple: (bool, str) - Success status and result message
        """
        from bot import MusicBot
        music_bot = MusicBot.get_instance(str(ctx.guild.id))
        
        # Input validation
        if count < 1:
            return False, "Loop count must be a positive number!"
            
        # If MusicBot doesn't have a voice client but Discord does, try to sync them
        if not music_bot.voice_client and ctx.guild.voice_client:
            print(f"Syncing voice client from Discord to MusicBot in _toggle_loop")
            music_bot.voice_client = ctx.guild.voice_client
            
            # Try to find the correct instance if this one doesn't have current_song
            if not music_bot.current_song:
                print(f"Looking for MusicBot instance with current song data in _toggle_loop")
                for instance_id, instance in MusicBot._instances.items():
                    if instance.current_song:
                        print(f"Found instance with song data: {instance_id}")
                        music_bot.current_song = instance.current_song
                        music_bot.is_playing = True
                        break
            
        # Check if the bot is in a voice channel
        if not music_bot.voice_client or not music_bot.voice_client.is_connected():
            return False, "Bot is not connected to a voice channel!"
            
        # Check if audio is actually playing
        if not music_bot.voice_client.is_playing():
            return False, "No audio is currently playing!"
            
        # Check if we have current song information
        if not music_bot.current_song:
            return False, "No song information available!"
        
        current_song_url = music_bot.current_song['url']
        is_song_looped = current_song_url in self.looped_songs
        
        if not is_song_looped:
            # Enable looping for this song
            self.looped_songs.add(current_song_url)
            
            # Add the song to the queue multiple times
            for _ in range(count):
                music_bot.queue.append(music_bot.current_song.copy())
            
            # Set up a callback to repeat the song when it finishes
            async def repeat_song(music_bot, ctx):
                # Only add the song back to the queue if it's still looped
                if current_song_url in self.looped_songs:
                    music_bot.queue.append(music_bot.current_song.copy())
                    
            # Set the callback
            music_bot.after_song_callback = lambda: asyncio.create_task(
                repeat_song(music_bot, ctx)  # We'll set the context later
            )
            
            return True, "Looping enabled for the current song."
        else:
            # Disable looping for this song
            self.looped_songs.remove(current_song_url)
            
            # Clear the callback when loop is disabled
            music_bot.after_song_callback = None
            
            # Remove all songs from queue that match the current song's URL
            music_bot.queue = [song for song in music_bot.queue if song['url'] != current_song_url]
            
            return True, "Looping disabled for the current song."

    @commands.command(name='loop', aliases=['repeat'])
    @check_dj_role()
    async def loop(self, ctx, count: int = 999):
        """
        Toggle loop for the current song.
        
        This command toggles looping for the currently playing song.
        When enabled, the song will be added back to the queue after it finishes playing.
        When disabled, the song will be removed from the queue.
        This command requires DJ permissions.
        
        Args:
            ctx: The command context
            count (int): Number of times to add the song to the queue (default: 999)
        """
        from bot import MusicBot
        music_bot = MusicBot.get_instance(str(ctx.guild.id))
        
        # Debug logging
        print(f"Loop command called for server {ctx.guild.id}")
        print(f"Server ID type: {type(ctx.guild.id)}")
        print(f"Voice client exists: {music_bot.voice_client is not None}")
        if music_bot.voice_client:
            print(f"Voice client is playing: {music_bot.voice_client.is_playing()}")
        print(f"Current song: {music_bot.current_song}")
        print(f"is_playing flag: {music_bot.is_playing}")
        
        # Check Discord's voice client directly
        if ctx.guild.voice_client:
            print(f"Discord voice client exists and is playing: {ctx.guild.voice_client.is_playing()}")
        else:
            print(f"Discord voice client does not exist")
        
        # Check all available instances
        print(f"Available MusicBot instances: {list(MusicBot._instances.keys())}")
        
        # Check if user is in voice chat
        if not ctx.author.voice:
            await ctx.send(embed=create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c, ctx=ctx))
            return
        
        # If MusicBot doesn't have a voice client but Discord does, try to sync them
        if not music_bot.voice_client and ctx.guild.voice_client:
            print(f"Syncing voice client from Discord to MusicBot")
            music_bot.voice_client = ctx.guild.voice_client
            
            # Try to find the correct instance if this one doesn't have current_song
            if not music_bot.current_song:
                print(f"Looking for MusicBot instance with current song data")
                for instance_id, instance in MusicBot._instances.items():
                    if instance.current_song:
                        print(f"Found instance with song data: {instance_id}")
                        music_bot.current_song = instance.current_song
                        music_bot.is_playing = True
                        break
            
        # Check if user is in the same voice chat as the bot
        if music_bot.voice_client and ctx.author.voice.channel != music_bot.voice_client.channel:
            await ctx.send(embed=create_embed("Error", "You must be in the same voice channel as the bot to use this command!", color=0xe74c3c, ctx=ctx))
            return
        
        success, result = await self._toggle_loop(ctx, count)
        
        if not success:
            await ctx.send(embed=create_embed("Error", result, color=0xe74c3c, ctx=ctx))
            return

        from bot import MusicBot
        music_bot = MusicBot.get_instance(str(ctx.guild.id))
        
        # Check if the song is now looped
        current_song_url = music_bot.current_song['url']
        is_song_looped = current_song_url in self.looped_songs

        color = 0x3498db if is_song_looped else 0xe74c3c
        title = "Looping enabled :repeat: " if is_song_looped else "Looping disabled :repeat: "
        description = f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})"

        embed = create_embed(
            title,
            description,
            color=color,
            thumbnail_url=music_bot.current_song.get('thumbnail'),
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
