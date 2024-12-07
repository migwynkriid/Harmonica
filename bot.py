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
from collections import deque
from datetime import datetime

# Force UTF-8 globally
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Create a log buffer using deque with max length
log_buffer = deque(maxlen=100)

# Override print to store logs
original_print = print
def custom_print(*args, **kwargs):
    output = " ".join(map(str, args))
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {output}"
    log_buffer.append(log_entry)
    original_print(*args, **kwargs)

print = custom_print

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
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
        self.download_queue = []  # Queue for tracks to be downloaded
        self.currently_downloading = False  # Flag to track download status
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

    async def process_download_queue(self, ctx):
        """Process the download queue sequentially"""
        if self.currently_downloading:
            return

        self.currently_downloading = True
        try:
            while self.download_queue:
                entry = self.download_queue[0]  # Peek at the next entry
                try:
                    print(f"Downloading next song in queue...")
                    song_info = await self._download_single_video(entry)
                    self.queue.append(song_info)
                    self.download_queue.pop(0)  # Remove the entry after successful download
                    
                    # If nothing is playing, start playback
                    if not self.voice_client.is_playing():
                        self.play_next(ctx)
                    
                except Exception as e:
                    print(f"Error downloading song: {str(e)}")
                    self.download_queue.pop(0)  # Remove failed entry
                    
        finally:
            self.currently_downloading = False

    def play_next(self, ctx):
        if len(self.queue) > 0:
            try:
                self.current_song = self.queue.pop(0)
                print(f"Playing next song: {self.current_song['title']}")
                print(f"Remaining songs in queue: {len(self.queue)}")
                print(f"Songs still downloading: {len(self.download_queue)}")
                
                if not os.path.exists(self.current_song['file_path']):
                    print(f"Error: File not found: {self.current_song['file_path']}")
                    if len(self.queue) > 0:
                        self.play_next(ctx)
                    return

                if not self.voice_client or not self.voice_client.is_connected():
                    print("Voice client not connected, attempting to reconnect...")
                    asyncio.run_coroutine_threadsafe(self.join_voice_channel(ctx), bot.loop)
                    return

                async def after_playing_coro(error):
                    if error:
                        print(f"Error in playback: {error}")
                        embed = self.create_embed("Error", f"An error occurred during playback: {str(error)}", color=0xe74c3c)
                        await ctx.send(embed=embed)
                    
                    print("Song finished playing, checking queue...")
                    print(f"Queue length: {len(self.queue)}")
                    print(f"Download queue length: {len(self.download_queue)}")
                    
                    # Start processing more downloads if needed
                    if not self.currently_downloading and self.download_queue:
                        asyncio.create_task(self.process_download_queue(ctx))
                    
                    # If queue is empty but we're still downloading, wait briefly
                    if len(self.queue) == 0 and self.download_queue:
                        print("Waiting for next song to finish downloading...")
                        await asyncio.sleep(1)  # Give a moment for download to complete
                        
                    if len(self.queue) > 0 or self.download_queue:
                        self.play_next(ctx)
                    else:
                        print("All songs finished, updating activity...")
                        self.update_activity()
                        if not self.download_queue:  # Only disconnect if nothing left to download
                            if self.voice_client and self.voice_client.is_connected():
                                await self.voice_client.disconnect()

                def after_playing(error):
                    asyncio.run_coroutine_threadsafe(after_playing_coro(error), bot.loop)

                audio_source = discord.FFmpegPCMAudio(
                    self.current_song['file_path'],
                    **FFMPEG_OPTIONS
                )
                
                self.voice_client.play(audio_source, after=after_playing)
                self.update_activity()
                
                # Send now playing message
                asyncio.run_coroutine_threadsafe(
                    ctx.send(
                        embed=self.create_embed(
                            "Now Playing",
                            f"[{self.current_song['title']}]({self.current_song['url']})",
                            color=0x2ecc71,
                            thumbnail_url=self.current_song.get('thumbnail')
                        )
                    ),
                    bot.loop
                )
                
            except Exception as e:
                print(f"Error in play_next: {str(e)}")
                if len(self.queue) > 0:
                    self.play_next(ctx)
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
            
            # First, get info to check if it's a playlist
            info_command = [
                ytdlp_path,
                '--cookies', cookies_path,
                '-J',  # Output json
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *info_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_message = stderr.decode() if stderr else "Unknown error"
                print(f"Error getting video info: {error_message}")
                raise Exception(f"Failed to get video info: {error_message}")

            try:
                video_info = json.loads(stdout.decode())
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {str(e)}")
                raise Exception("Failed to parse video information")

            # Handle playlists
            if video_info.get('_type') == 'playlist':
                if not video_info.get('entries'):
                    raise Exception("Playlist is empty")
                
                # Return a special indicator that this is a playlist
                return {
                    'is_playlist': True,
                    'entries': video_info['entries']
                }

            # Single video handling
            return await self._download_single_video(video_info)
            
        except Exception as e:
            print(f"Error downloading song: {str(e)}")
            raise Exception(f"Failed to download the song: {str(e)}")

    async def _download_single_video(self, video_info):
        """Helper method to download a single video"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ytdlp_path = os.path.join(current_dir, 'yt-dlp.exe')
            cookies_path = os.path.join(current_dir, 'cookies.txt')

            video_id = video_info.get('id')
            if not video_id:
                raise Exception("Could not get video ID")

            # Prepare the download command
            command = [
                ytdlp_path,
                '--cookies', cookies_path,
                '-x',  # Extract audio
                '--audio-format', 'mp3',
                '--audio-quality', '96K',
                '--embed-thumbnail',
                '--paths', DOWNLOADS_DIR,
                '--output', '%(id)s.%(ext)s',
                '--no-playlist',  # Only download the specific video
                f'https://www.youtube.com/watch?v={video_id}'  # Use direct video URL
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
            
            file_path = os.path.join(DOWNLOADS_DIR, f"{video_id}.mp3")
            
            if not os.path.exists(file_path):
                raise Exception(f"Downloaded file not found at {file_path}")
            
            return {
                'title': video_info.get('title', video_id),
                'file_path': file_path,
                'duration': video_info.get('duration', 0),
                'id': video_id,
                'thumbnail': video_info.get('thumbnail'),
                'url': f'https://www.youtube.com/watch?v={video_id}'
            }
        except Exception as e:
            print(f"Error downloading single video: {str(e)}")
            raise e

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
        
        result = await music_bot.download_song(query)
        
        # Handle playlist
        if isinstance(result, dict) and result.get('is_playlist'):
            if not await music_bot.join_voice_channel(ctx):
                await status_msg.edit(
                    embed=music_bot.create_embed(
                        "Error",
                        "Failed to join voice channel. Please make sure you're in a voice channel.",
                        color=0xe74c3c
                    )
                )
                return
                
            playlist_length = len(result['entries'])
            await status_msg.edit(
                embed=music_bot.create_embed(
                    "Processing Playlist",
                    f"Starting playlist with {playlist_length} songs...",
                    color=0xf1c40f
                )
            )
            
            try:
                # Download first song immediately
                first_song = await music_bot._download_single_video(result['entries'][0])
                music_bot.queue.append(first_song)
                
                # Add remaining songs to download queue
                music_bot.download_queue.extend(result['entries'][1:])
                
                # Start playing first song
                if not music_bot.voice_client.is_playing():
                    music_bot.play_next(ctx)
                
                # Start background download of next songs
                asyncio.create_task(music_bot.process_download_queue(ctx))
                
                await status_msg.edit(
                    embed=music_bot.create_embed(
                        "Playlist Started",
                        f"Playing first song. {playlist_length - 1} more songs will be processed in the background.",
                        color=0x2ecc71
                    )
                )
                
            except Exception as e:
                print(f"Error starting playlist: {str(e)}")
                await status_msg.edit(
                    embed=music_bot.create_embed(
                        "Error",
                        f"An error occurred while starting the playlist: {str(e)}",
                        color=0xe74c3c
                    )
                )
            
            return
        
        # Handle single video
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
            music_bot.queue.append(result)
            await status_msg.edit(
                embed=music_bot.create_embed(
                    "Added to Queue",
                    f"[{result['title']}]({result['url']})",
                    color=0x3498db,
                    thumbnail_url=result.get('thumbnail')
                )
            )
        else:
            music_bot.queue.append(result)
            music_bot.play_next(ctx)
            await status_msg.edit(
                embed=music_bot.create_embed(
                    "Now Playing",
                    f"[{result['title']}]({result['url']})",
                    color=0x2ecc71,
                    thumbnail_url=result.get('thumbnail')
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

@bot.command(name='log')
async def log(ctx):
    """Display the last 100 console log entries"""
    try:
        if not log_buffer:
            await ctx.send("No logs available.")
            return

        # Join all log entries with newlines
        logs = "\n".join(list(log_buffer))
        
        # Split logs into chunks of 1900 characters (leaving room for code block formatting)
        chunks = []
        while logs:
            if len(logs) <= 1900:
                chunks.append(logs)
                break
            
            # Find the last newline before 1900 characters
            split_index = logs[:1900].rfind('\n')
            if split_index == -1:
                split_index = 1900
            
            chunks.append(logs[:split_index])
            logs = logs[split_index:].lstrip()
        
        # Send each chunk as a separate message
        for chunk in chunks:
            await ctx.send(f"```\n{chunk}\n```")
            
    except Exception as e:
        print(f"Error sending logs: {str(e)}")
        await ctx.send("An error occurred while sending the logs.")

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
