import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp
import asyncio
import re
import unicodedata
import sys
import locale
import time
import shutil
from pathlib import Path
from discord.ext import tasks
import json

# Force UTF-8 globally
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Create downloads directory if it doesn't exist
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# YouTube DL options
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'postprocessors': [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '96',
        },
        {
            'key': 'EmbedThumbnail',
        }
    ],
    'writethumbnail': True,
    'windowsfilenames': True,
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'force_generic_extractor': False,
    'outtmpl': '%(id)s.%(ext)s',
    'cookies': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')  # Add cookies path here
}

# FFmpeg options
FFMPEG_OPTIONS = {
    'executable': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe'),
    'options': '-vn',
}

class MusicBot:
    def __init__(self):
        self.voice_client = None
        self.queue = []
        self.current_song = None
        self.last_activity = time.time()
        self.inactivity_timeout = 1800  # 30 minutes in seconds
        self._inactivity_task = None
        # Start the cleanup task
        self.clear_downloads.start()

    def update_activity(self):
        """Update the last activity timestamp and bot status"""
        self.last_activity = time.time()
        
        async def set_activity():
            if self.current_song and (self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused())):
                # If a song is playing/paused, show it in the status
                status = f" {self.current_song['title']}"
                await bot.change_presence(activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name=status
                ))
            else:
                # If no song is playing, show default status
                await bot.change_presence(activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name="!play to start music"
                ))
        
        # Schedule the coroutine to run
        asyncio.run_coroutine_threadsafe(set_activity(), bot.loop)

    async def start_inactivity_checker(self):
        """Start the inactivity checker"""
        self.check_inactivity.start()

    @tasks.loop(seconds=60)  # Check every minute
    async def check_inactivity(self):
        """Check for inactivity and leave voice if inactive too long"""
        try:
            if self.voice_client and self.voice_client.is_connected():
                # If not playing and inactive for too long
                if not self.voice_client.is_playing() and time.time() - self.last_activity > self.inactivity_timeout:
                    print(f"Leaving voice channel due to {self.inactivity_timeout} seconds of inactivity")
                    await self.voice_client.disconnect()
                    self.clear_queue()
        except Exception as e:
            print(f"Error in inactivity checker: {str(e)}")

    @check_inactivity.before_loop
    async def before_check_inactivity(self):
        """Wait for the bot to be ready before starting the inactivity checker"""
        await bot.wait_until_ready()

    def sanitize_filename(self, filename):
        """Sanitize filename to handle special characters"""
        # Remove non-ASCII characters or replace with ASCII equivalents
        filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode('ASCII')
        # Remove any characters that aren't alphanumeric, dash, underscore, or dot
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        return filename

    async def join_voice_channel(self, ctx):
        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to use this command!")
            return False
        
        self.update_activity()  # Update activity when joining
        voice_channel = ctx.author.voice.channel
        try:
            if ctx.voice_client is None:
                self.voice_client = await voice_channel.connect()
            else:
                await ctx.voice_client.move_to(voice_channel)
                self.voice_client = ctx.voice_client
            return True
        except Exception as e:
            print(f"Error joining voice channel: {str(e)}")
            return False

    def create_embed(self, title, description, color=0x3498db, thumbnail_url=None):
        """Create a Discord embed with consistent styling"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        return embed

    def play_next(self, ctx):
        if len(self.queue) > 0:
            try:
                self.current_song = self.queue.pop(0)
                print(f"Attempting to play: {self.current_song['file_path']}")
                
                if not os.path.exists(self.current_song['file_path']):
                    print(f"Error: File not found: {self.current_song['file_path']}")
                    return

                if not self.voice_client or not self.voice_client.is_connected():
                    print("Voice client not connected, cannot play audio")
                    return

                async def after_playing_coro(error):
                    if error:
                        print(f"Error in playback: {error}")
                        embed = self.create_embed("Error", f"An error occurred during playback: {str(error)}", color=0xe74c3c)
                        await ctx.send(embed=embed)
                    
                    if len(self.queue) == 0:
                        self.update_activity()
                        if self.voice_client and self.voice_client.is_connected():
                            await self.voice_client.disconnect()
                    else:
                        self.play_next(ctx)

                def after_playing(error):
                    asyncio.run_coroutine_threadsafe(after_playing_coro(error), bot.loop)

                audio_source = discord.FFmpegPCMAudio(
                    self.current_song['file_path'],
                    **FFMPEG_OPTIONS
                )
                
                self.voice_client.play(audio_source, after=after_playing)
                self.update_activity()
                print(f"Started playing: {self.current_song['title']}")
            except Exception as e:
                print(f"Error in play_next: {str(e)}")
        else:
            self.current_song = None
            self.update_activity()

    async def download_song(self, url):
        try:
            print(f"Attempting to download from URL: {url}")
            
            # Get the paths
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ytdlp_path = os.path.join(current_dir, 'yt-dlp.exe')
            cookies_path = os.path.join(current_dir, 'cookies.txt')
            
            # Prepare the command
            command = [
                ytdlp_path,
                '--cookies', cookies_path,
                '-x',  # Extract audio
                '--audio-format', 'mp3',
                '--audio-quality', '96K',
                '--embed-thumbnail',
                '--paths', DOWNLOADS_DIR,
                '--output', '%(id)s.%(ext)s',
                '--no-playlist',
                url
            ]
            
            # Run yt-dlp command
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_message = stderr.decode() if stderr else "Unknown error"
                print(f"yt-dlp error: {error_message}")
                raise Exception(f"Failed to download: {error_message}")
            
            # Extract video ID from the URL or output
            output = stdout.decode()
            video_id_match = re.search(r'[a-zA-Z0-9_-]{11}', url)
            if not video_id_match:
                raise Exception("Could not extract video ID from URL")
            
            video_id = video_id_match.group(0)
            file_path = os.path.join(DOWNLOADS_DIR, f"{video_id}.mp3")
            
            if not os.path.exists(file_path):
                raise Exception(f"Downloaded file not found at {file_path}")
            
            # Get video info for title and thumbnail
            info_command = [
                ytdlp_path,
                '--cookies', cookies_path,
                '-J',  # Output json
                '--no-playlist',
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *info_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                # If we can't get info, at least return basic info
                return {
                    'title': video_id,
                    'file_path': file_path,
                    'duration': 0,
                    'id': video_id,
                    'thumbnail': None,
                    'url': url
                }
            
            try:
                video_info = json.loads(stdout.decode())
                return {
                    'title': video_info.get('title', video_id),
                    'file_path': file_path,
                    'duration': video_info.get('duration', 0),
                    'id': video_id,
                    'thumbnail': video_info.get('thumbnail'),
                    'url': url
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, return basic info
                return {
                    'title': video_id,
                    'file_path': file_path,
                    'duration': 0,
                    'id': video_id,
                    'thumbnail': None,
                    'url': url
                }
            
        except Exception as e:
            print(f"Error downloading song: {str(e)}")
            raise Exception(f"Failed to download the song: {str(e)}")

    def clear_queue(self):
        """Clear the song queue and stop current playback"""
        self.queue = []
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        self.current_song = None

    @tasks.loop(hours=24)
    async def clear_downloads(self):
        """Clear the downloads folder daily at midnight"""
        downloads_dir = Path(DOWNLOADS_DIR)
        if downloads_dir.exists():
            # Remove all contents of the downloads directory
            for item in downloads_dir.iterdir():
                if item.is_file():
                    try:
                        if not self.voice_client or not self.voice_client.is_playing() or str(item) != self.current_song.get('file_path', ''):
                            item.unlink()
                    except Exception as e:
                        print(f"Error deleting file {item}: {e}")
                elif item.is_dir():
                    try:
                        shutil.rmtree(item)
                    except Exception as e:
                        print(f"Error deleting directory {item}: {e}")
            print(f"Cleared contents of {downloads_dir}")

    @clear_downloads.before_loop
    async def before_clear_downloads(self):
        """Wait until midnight to start the task"""
        await bot.wait_until_ready()
        # Calculate time until next midnight
        now = time.time()
        seconds_until_midnight = 86400 - (now % 86400)  # 86400 seconds in a day
        await asyncio.sleep(seconds_until_midnight)

# Global variable for music bot instance
music_bot = None

@bot.event
async def on_ready():
    global music_bot
    print(f'{bot.user} has connected to Discord!')
    music_bot = MusicBot()
    await music_bot.start_inactivity_checker()

@bot.command(name='play')
async def play(ctx, *, query):
    """Download and play a song from YouTube"""
    try:
        music_bot.update_activity()
        status_embed = music_bot.create_embed("Processing", "Processing your request...", color=0xf1c40f)
        status_msg = await ctx.send(embed=status_embed)
        
        song_info = await music_bot.download_song(query)
        
        if not await music_bot.join_voice_channel(ctx):
            await status_msg.edit(
                embed=music_bot.create_embed(
                    "Error",
                    "Failed to join voice channel. Please make sure you're in a voice channel.",
                    color=0xe74c3c
                )
            )
            return
        
        if music_bot.voice_client and music_bot.voice_client.is_playing():
            music_bot.queue.append(song_info)
            await status_msg.edit(
                embed=music_bot.create_embed(
                    "Added to Queue",
                    f"[{song_info['title']}]({song_info['url']})",
                    color=0x3498db,
                    thumbnail_url=song_info.get('thumbnail')
                )
            )
        else:
            music_bot.queue.append(song_info)
            music_bot.play_next(ctx)
            await status_msg.edit(
                embed=music_bot.create_embed(
                    "Now Playing",
                    f"[{song_info['title']}]({song_info['url']})",
                    color=0x2ecc71,
                    thumbnail_url=song_info.get('thumbnail')
                )
            )

    except Exception as e:
        print(f"Error in play command: {str(e)}")
        await status_msg.edit(
            embed=music_bot.create_embed(
                "Error",
                f"An error occurred: {str(e)}",
                color=0xe74c3c
            )
        )

@bot.command(name='pause')
async def pause(ctx):
    """Pause the currently playing song"""
    try:
        music_bot.update_activity()
        if music_bot.voice_client and music_bot.voice_client.is_playing():
            music_bot.voice_client.pause()
            await ctx.send(
                embed=music_bot.create_embed(
                    "Paused ",
                    music_bot.current_song['title'],
                    color=0xf1c40f
                )
            )
        else:
            await ctx.send(
                embed=music_bot.create_embed(
                    "Error",
                    "Nothing is playing right now.",
                    color=0xe74c3c
                )
            )
    except Exception as e:
        await ctx.send(
            embed=music_bot.create_embed(
                "Error",
                f"Error: {str(e)}",
                color=0xe74c3c
            )
        )

@bot.command(name='resume')
async def resume(ctx):
    """Resume the currently paused song"""
    try:
        music_bot.update_activity()
        if music_bot.voice_client and music_bot.voice_client.is_paused():
            music_bot.voice_client.resume()
            await ctx.send(
                embed=music_bot.create_embed(
                    "Resumed ",
                    music_bot.current_song['title'],
                    color=0x2ecc71
                )
            )
        else:
            await ctx.send(
                embed=music_bot.create_embed(
                    "Error",
                    "Nothing is paused right now.",
                    color=0xe74c3c
                )
            )
    except Exception as e:
        await ctx.send(
            embed=music_bot.create_embed(
                "Error",
                f"Error: {str(e)}",
                color=0xe74c3c
            )
        )

@bot.command(name='stop')
async def stop(ctx):
    """Stop playback, clear queue, and leave the voice channel"""
    try:
        music_bot.clear_queue()
        if music_bot.voice_client and music_bot.voice_client.is_connected():
            await music_bot.voice_client.disconnect()
        await ctx.send(
            embed=music_bot.create_embed(
                "Stopped ",
                "Stopped playback and cleared queue.",
                color=0x95a5a6
            )
        )
    except Exception as e:
        await ctx.send(
            embed=music_bot.create_embed(
                "Error",
                f"An error occurred while stopping: {str(e)}",
                color=0xe74c3c
            )
        )

@bot.command(name='skip')
async def skip(ctx):
    """Skip the current song"""
    if music_bot.voice_client and (music_bot.voice_client.is_playing() or music_bot.voice_client.is_paused()):
        music_bot.voice_client.stop()
        await ctx.send(
            embed=music_bot.create_embed(
                "Skipped ",
                "Skipped the current song.",
                color=0x3498db
            )
        )
    else:
        await ctx.send(
            embed=music_bot.create_embed(
                "Error",
                "Nothing is playing to skip.",
                color=0xe74c3c
            )
        )

@bot.command(name='queue')
async def queue(ctx):
    """Show the current queue"""
    if not music_bot.queue and not music_bot.current_song:
        await ctx.send(
            embed=music_bot.create_embed(
                "Queue ",
                "The queue is empty.",
                color=0x95a5a6
            )
        )
        return

    queue_text = ""
    if music_bot.current_song:
        queue_text += f"**Now Playing:**\n[{music_bot.current_song['title']}]({music_bot.current_song['url']})\n\n"
    
    if music_bot.queue:
        queue_text += "**Up Next:**\n"
        for i, song in enumerate(music_bot.queue, 1):
            queue_text += f"{i}. [{song['title']}]({song['url']})\n"
    
    await ctx.send(
        embed=music_bot.create_embed(
            "Queue ",
            queue_text,
            color=0x3498db
        )
    )

@bot.command(name='leave')
async def leave(ctx):
    """Leave the voice channel"""
    if music_bot.voice_client and music_bot.voice_client.is_connected():
        music_bot.clear_queue()  # Clear queue when leaving
        await music_bot.voice_client.disconnect()
        await ctx.send(
            embed=music_bot.create_embed(
                "Left",
                "Left the voice channel.",
                color=0x95a5a6
            )
        )
    else:
        await ctx.send(
            embed=music_bot.create_embed(
                "Error",
                "I'm not in a voice channel.",
                color=0xe74c3c
            )
        )

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN'))
