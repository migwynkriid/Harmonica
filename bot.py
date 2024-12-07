import os
import discord
from discord.ext import commands, tasks
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
from pytz import timezone  # Import timezone from pytz
import pytz  # Import pytz for timezone handling

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

# Constants
DOWNLOADS_DIR = os.path.join(os.getcwd(), 'downloads')
OWNER_ID = 220301180562046977  # Add owner ID constant
RESTART_HOUR = 3  # 3 AM EST

# Create downloads directory if it doesn't exist
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

def clear_downloads_folder():
    """Clear all files in the downloads folder"""
    if os.path.exists(DOWNLOADS_DIR):
        for file in os.listdir(DOWNLOADS_DIR):
            file_path = os.path.join(DOWNLOADS_DIR, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f'Error deleting {file_path}: {e}')

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

# YouTube DL options
YTDL_OPTIONS = {
    # Format selection priority:
    # 1. opus audio only at 96kbps or less (if available)
    # 2. m4a audio only at 96kbps or less (if opus not available)
    # 3. best audio stream at 96kbps or less
    # 4. Fallback to any audio if no 96kbps stream available
    'format': 'bestaudio[acodec=opus][abr<=96]/bestaudio[ext=m4a][abr<=96]/bestaudio[abr<=96]/bestaudio',
    'outtmpl': '%(id)s.%(ext)s',
    'extract_audio': True,
    'audioformat': 'opus',  # Discord works best with opus
    'preferredcodec': 'opus',
    'nopostoverwrites': True,
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
}

# FFmpeg options (simplified, only used for streaming)
FFMPEG_OPTIONS = {
    'executable': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe'),
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',  # Added reconnect options for stability
}

class CancelButton(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot = bot_instance
        self.cancelled = False
        self.current_file = None

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            self.cancelled = True
            if self.bot.current_process and hasattr(self.bot.current_process, 'terminate'):
                try:
                    self.bot.current_process.terminate()
                except:
                    pass
            self.bot.current_process = None
            
            # Clean up the current file if it exists
            if self.current_file and os.path.exists(self.current_file):
                try:
                    os.remove(self.current_file)
                    print(f"Cleaned up cancelled file: {self.current_file}")
                except Exception as e:
                    print(f"Error cleaning up file: {str(e)}")

            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="Cancelled",
                    description="Download process cancelled by user.",
                    color=0xe74c3c
                ),
                view=None
            )
        except Exception as e:
            print(f"Error in cancel button: {str(e)}")

class DownloadProgress:
    def __init__(self, status_msg, view):
        self.status_msg = status_msg
        self.view = view
        self.last_update = 0
        self.title = ""
        
    def create_progress_bar(self, percentage, width=20):
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return bar
        
    async def progress_hook(self, d):
        if d['status'] == 'downloading':
            # Only update once per second to avoid rate limits
            current_time = time.time()
            if current_time - self.last_update < 1:
                return
                
            self.last_update = current_time
            
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                speed = d.get('speed', 0)
                if total == 0:
                    return
                
                percentage = (downloaded / total) * 100
                progress_bar = self.create_progress_bar(percentage)
                
                # Format speed in MB/s
                speed_mb = speed / 1024 / 1024 if speed else 0
                
                # Create status message
                status = f"Downloading: {self.title}\n"
                status += f"\n{progress_bar} {percentage:.1f}%\n"
                status += f"Speed: {speed_mb:.1f} MB/s"
                
                # Update embed
                embed = discord.Embed(
                    title="Downloading",
                    description=status,
                    color=0xf1c40f
                )
                
                asyncio.create_task(self.status_msg.edit(embed=embed))
                
            except Exception as e:
                print(f"Error updating progress: {str(e)}")

class MusicBot:
    def __init__(self):
        """Initialize the music bot"""
        self.voice_client = None
        self.queue = []  # Music queue
        self.download_queue = asyncio.Queue()  # Queue for tracks to be downloaded
        self.currently_downloading = False
        self.current_song = None
        self.current_process = None
        self.command_queue = asyncio.Queue()  # Queue for play commands
        self.command_processor_task = None  # Task for processing commands
        self.status_messages = {}
        self.current_command_msg = None
        self.current_command_author = None
        self.downloads_dir = DOWNLOADS_DIR
        self.cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
        self.last_update = 0  # Initialize last_update for progress tracking
        self.inactivity_timeout = 1800  # 30 minutes in seconds
        self._inactivity_task = None
        self.last_activity = time.time()
        self.bot_loop = None  # Store bot's event loop
        self.loop_mode = False  # Track if loop mode is enabled
        self.download_lock = asyncio.Lock()  # Lock for download synchronization

    async def setup(self, bot_loop):
        """Setup the bot with the event loop"""
        self.bot_loop = bot_loop
        await self.start_command_processor()
        # Start the download processor
        asyncio.create_task(self.process_download_queue())

    async def start_command_processor(self):
        """Start the command processor task"""
        if self.command_processor_task is None:
            self.command_processor_task = asyncio.create_task(self.process_command_queue())
            print("Command processor started")

    async def process_command_queue(self):
        """Process commands from the queue one at a time"""
        while True:
            try:
                # Get the next command from the queue
                ctx, query = await self.command_queue.get()
                print(f"Processing command: !play {query}")

                try:
                    # Process the play command
                    await self._handle_play_command(ctx, query)
                except Exception as e:
                    print(f"Error processing command: {e}")
                    error_embed = self.create_embed("Error", f"Failed to process command: {str(e)}", color=0xe74c3c)
                    await self.update_or_send_message(ctx, error_embed)
                finally:
                    # Mark the command as done
                    self.command_queue.task_done()
            except Exception as e:
                print(f"Error in command processor: {str(e)}")
                await asyncio.sleep(1)  # Prevent tight loop on error

    async def _handle_play_command(self, ctx, query):
        """Internal method to handle a single play command"""
        if not ctx.voice_client and not await self.join_voice_channel(ctx):
            raise Exception("Could not join voice channel")

        # Create cancel button view
        view = CancelButton(self)
        
        # Send initial status message
        status_embed = self.create_embed("Processing", f"Processing query: {query}", color=0x3498db)
        status_msg = await self.update_or_send_message(ctx, status_embed, view=view)

        # Create download info
        download_info = {
            'query': query,
            'ctx': ctx,
            'status_msg': status_msg,
            'view': view
        }

        # Add to download queue
        await self.download_queue.put(download_info)
        print(f"Added to download queue: {query}")

    async def process_download_queue(self):
        """Process the download queue sequentially"""
        while True:
            try:
                # Get the next download task
                download_info = await self.download_queue.get()
                
                # Extract info
                query = download_info['query']
                ctx = download_info['ctx']
                status_msg = download_info['status_msg']
                view = download_info['view']

                try:
                    async with self.download_lock:  # Ensure only one download at a time
                        self.currently_downloading = True
                        print(f"Starting download: {query}")
                        
                        # Download the song
                        result = await self.download_song(query, status_msg, view)
                        
                        if not result:
                            if not view.cancelled:
                                error_embed = self.create_embed("Error", "Failed to download song", color=0xe74c3c)
                                await self.update_or_send_message(ctx, error_embed)
                            continue

                        # Add to queue or play immediately
                        if self.voice_client and self.voice_client.is_playing():
                            self.queue.append(result)
                            queue_embed = self.create_embed(
                                "Added to Queue", 
                                f"[🎵 {result['title']}]({result['url']})", 
                                thumbnail_url=result.get('thumbnail')
                            )
                            await ctx.send(embed=queue_embed)
                        else:
                            self.queue.append(result)
                            await self.play_next(ctx)

                except Exception as e:
                    print(f"Error processing download: {str(e)}")
                    if not view.cancelled:
                        error_embed = self.create_embed("Error", f"Failed to process: {str(e)}", color=0xe74c3c)
                        await self.update_or_send_message(ctx, error_embed)
                
                finally:
                    self.currently_downloading = False
                    self.download_queue.task_done()

            except Exception as e:
                print(f"Error in download queue processor: {str(e)}")
                await asyncio.sleep(1)  # Prevent tight loop on error

    async def start_inactivity_checker(self):
        """Start the inactivity checker"""
        try:
            await self.check_inactivity()
        except Exception as e:
            print(f"Error starting inactivity checker: {str(e)}")

    async def check_inactivity(self):
        """Check for inactivity and leave voice if inactive too long"""
        while True:
            try:
                if self.voice_client and self.voice_client.is_connected():
                    # If not playing and inactive for too long
                    if not self.voice_client.is_playing() and time.time() - self.last_activity > self.inactivity_timeout:
                        print(f"Leaving voice channel due to {self.inactivity_timeout} seconds of inactivity")
                        await self.voice_client.disconnect()
                        self.clear_queue()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Error in inactivity checker: {str(e)}")
                await asyncio.sleep(60)  # Still wait before next check even if there's an error

    def clear_queue(self):
        """Clear the queue and current song"""
        self.queue = []
        self.current_song = None
        # Clear download queue
        while not self.download_queue.empty():
            try:
                self.download_queue.get_nowait()
                self.download_queue.task_done()
            except asyncio.QueueEmpty:
                break

    async def join_voice_channel(self, ctx):
        """Join the user's voice channel"""
        if not ctx.author.voice:
            await ctx.send(embed=self.create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c))
            return False

        try:
            channel = ctx.author.voice.channel
            if not self.voice_client:
                self.voice_client = await channel.connect(self_deaf=True)  # Add self_deaf=True to suppress join sound
            elif self.voice_client.channel != channel:
                await self.voice_client.move_to(channel)
            return True
        except Exception as e:
            print(f"Error joining voice channel: {str(e)}")
            await ctx.send(embed=self.create_embed("Error", "Failed to join voice channel!", color=0xe74c3c))
            return False

    def sanitize_filename(self, filename):
        """Sanitize filename to handle special characters"""
        # Remove non-ASCII characters or replace with ASCII equivalents
        filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode('ASCII')
        # Remove any characters that aren't alphanumeric, dash, underscore, or dot
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        return filename

    async def update_or_send_message(self, ctx, embed, view=None, force_new=False):
        """Update existing message or send a new one if none exists or if it's a new command"""
        try:
            # Send new message if:
            # 1. force_new is True
            # 2. No current message exists
            # 3. Different user is running a command
            # 4. Same user but different channel
            if (force_new or 
                not self.current_command_msg or 
                ctx.author.id != self.current_command_author or 
                ctx.channel.id != self.current_command_msg.channel.id):
                
                self.current_command_msg = await ctx.send(embed=embed, view=view)
                self.current_command_author = ctx.author.id
            else:
                await self.current_command_msg.edit(embed=embed, view=view)
            
            return self.current_command_msg
        except Exception as e:
            print(f"Error updating message: {str(e)}")
            # If editing fails, send a new message
            self.current_command_msg = await ctx.send(embed=embed, view=view)
            self.current_command_author = ctx.author.id
            return self.current_command_msg

    async def play_next(self, ctx):
        """Play the next song in the queue"""
        if len(self.queue) > 0:
            try:
                previous_song = self.current_song
                self.current_song = self.queue.pop(0)
                print(f"Playing next song: {self.current_song['title']}")
                if len(self.queue) > 0:
                    print(f"Remaining songs in queue: {len(self.queue)}")
                if not self.download_queue.empty():
                    print(f"Songs still downloading: {self.download_queue.qsize()}")
                
                # Delete the download complete message if it exists
                if self.current_song.get('status_message'):
                    try:
                        await self.current_song['status_message'].delete()
                    except:
                        pass
                
                if not os.path.exists(self.current_song['file_path']):
                    print(f"Error: File not found: {self.current_song['file_path']}")
                    if len(self.queue) > 0:
                        await self.play_next(ctx)
                    return

                if not self.voice_client or not self.voice_client.is_connected():
                    print("Voice client not connected, attempting to reconnect...")
                    await self.join_voice_channel(ctx)
                    return

                # Only send Now Playing message if it's a different song
                if not previous_song or previous_song['url'] != self.current_song['url']:
                    now_playing_embed = self.create_embed(
                        "Now Playing",
                        f"[🎵 {self.current_song['title']}]({self.current_song['url']})",
                        thumbnail_url=self.current_song.get('thumbnail')
                    )
                    await ctx.send(embed=now_playing_embed)
                
                # Reset current message tracking for next command
                self.current_command_msg = None
                self.current_command_author = None

                # Play the audio file
                audio_source = discord.FFmpegPCMAudio(self.current_song['file_path'])
                self.voice_client.play(
                    audio_source,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.after_playing_coro(e, ctx), self.voice_client.loop
                    )
                )
            except Exception as e:
                print(f"Error in play_next: {str(e)}")
                if len(self.queue) > 0:
                    await self.play_next(ctx)
        else:
            self.current_song = None
            self.update_activity()

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

    async def update_or_send_message(self, ctx, embed, view=None, force_new=False):
        """Update existing message or send a new one if none exists or if it's a new command"""
        try:
            # Send new message if:
            # 1. force_new is True
            # 2. No current message exists
            # 3. Different user is running a command
            # 4. Same user but different channel
            if (force_new or 
                not self.current_command_msg or 
                ctx.author.id != self.current_command_author or 
                ctx.channel.id != self.current_command_msg.channel.id):
                
                self.current_command_msg = await ctx.send(embed=embed, view=view)
                self.current_command_author = ctx.author.id
            else:
                await self.current_command_msg.edit(embed=embed, view=view)
            
            return self.current_command_msg
        except Exception as e:
            print(f"Error updating message: {str(e)}")
            # If editing fails, send a new message
            self.current_command_msg = await ctx.send(embed=embed, view=view)
            self.current_command_author = ctx.author.id
            return self.current_command_msg

    async def download_song(self, query, status_msg=None, view=None):
        """Download a song from YouTube"""
        try:
            # Ensure downloads directory exists
            if not os.path.exists(self.downloads_dir):
                os.makedirs(self.downloads_dir)

            # Base yt-dlp options
            ydl_opts = {
                **YTDL_OPTIONS,  # Use base options
                'outtmpl': os.path.join(self.downloads_dir, '%(id)s.%(ext)s'),
                'cookiefile': self.cookie_file if os.path.exists(self.cookie_file) else None,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Check if it's a direct YouTube URL
                if 'youtube.com' in query or 'youtu.be' in query:
                    info = await asyncio.get_event_loop().run_in_executor(None, ydl.extract_info, query, True)
                else:
                    # Search for the video
                    info = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: ydl.extract_info(f"ytsearch:{query}", download=True)['entries'][0]
                    )

                if not info:
                    raise Exception("Could not find video")

                # Get video ID and construct clean filename
                video_id = info['id']
                title = info['title']
                url = f"https://youtube.com/watch?v={video_id}"
                # Use the actual downloaded file extension
                file_path = os.path.join(self.downloads_dir, f"{video_id}.{info['ext']}")

                # Add a small delay to ensure file operations are complete
                await asyncio.sleep(1)

                # Verify file exists and is accessible
                max_retries = 3
                retry_delay = 1
                for attempt in range(max_retries):
                    try:
                        if not os.path.exists(file_path):
                            raise FileNotFoundError(f"Downloaded file not found: {file_path}")
                        
                        # Try to open the file to verify it's not locked
                        with open(file_path, 'rb') as f:
                            pass
                        
                        # If we get here, the file is accessible
                        break
                    except (FileNotFoundError, PermissionError) as e:
                        if attempt == max_retries - 1:
                            raise Exception(f"Could not access downloaded file after {max_retries} attempts: {str(e)}")
                        print(f"Retry {attempt + 1}/{max_retries}: Waiting for file to be accessible...")
                        await asyncio.sleep(retry_delay)

                # Return song info
                return {
                    'title': title,
                    'url': url,
                    'file_path': file_path,
                    'thumbnail': info.get('thumbnail'),
                    'status_message': status_msg
                }

        except Exception as e:
            print(f"Error downloading song: {str(e)}")
            if status_msg and not (view and view.cancelled):
                error_embed = self.create_embed("Error", f"Failed to download: {str(e)}", color=0xe74c3c)
                await status_msg.edit(embed=error_embed)
            
            # Cleanup any partial downloads
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as cleanup_error:
                print(f"Error cleaning up failed download: {str(cleanup_error)}")
            
            return None

    def download_hook(self, d, status_msg, view):
        """Handle download progress updates"""
        if not status_msg or not self.bot_loop:
            return

        if d['status'] == 'downloading':
            # Only update once per second to avoid rate limits
            current_time = time.time()
            if current_time - self.last_update < 1:
                return
                
            self.last_update = current_time
            
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                speed = d.get('speed', 0)
                if total == 0:
                    return
                
                percentage = (downloaded / total) * 100
                
                # Create status message
                status = f"Downloading: {d.get('filename', 'Unknown')}\n"
                status += f"\n{percentage:.1f}%\n"
                status += f"Speed: {speed / 1024 / 1024:.1f} MB/s"
                
                # Update embed
                embed = discord.Embed(
                    title="Downloading",
                    description=status,
                    color=0xf1c40f
                )
                
                # Use the stored bot loop
                future = asyncio.run_coroutine_threadsafe(
                    status_msg.edit(embed=embed),
                    self.bot_loop
                )
                future.result()  # Wait for the edit to complete
                
            except Exception as e:
                print(f"Error updating progress: {str(e)}")

    async def _download_single_video(self, video_info, status_msg=None, view=None):
        """Helper method to download a single video"""
        output_file = None
        try:
            # Check if cancelled
            if view and view.cancelled:
                return None

            video_id = video_info.get('id')
            if not video_id:
                raise Exception("No video ID found in info")

            title = video_info.get('title', 'Unknown Title')
            url = video_info.get('webpage_url', video_info.get('url'))
            thumbnail = video_info.get('thumbnail')
            
            # Use only video ID for filename
            output_file = os.path.join(self.downloads_dir, f"{video_id}.mp3")

            # Update the view's current file
            if view:
                view.current_file = output_file

            # Skip download if file already exists
            if os.path.exists(output_file):
                print(f"File already exists: {output_file}")
                return {
                    'title': title,
                    'url': url,
                    'file_path': output_file,
                    'thumbnail': thumbnail
                }

            # Create progress tracker
            progress = DownloadProgress(status_msg, view)
            progress.title = title

            # Download the video with progress updates
            download_cmd = [
                'yt-dlp',
                '-f', 'bestaudio',  # Get best audio only
                '-x',  # Extract audio
                '--audio-format', 'mp3',
                '--audio-quality', '96K',  # Set to 96kbps
                '--newline',  # Force progress to new lines
                '--progress-template', '%(progress.downloaded_bytes)s %(progress.total_bytes)s %(progress.speed)s',
                '--cookies', '../cookies.txt',  # Adjust cookies path since we're in downloads dir
                '--no-keep-video',  # Don't keep the video file after conversion
                '--write-thumbnail',  # Download thumbnail
                '--embed-thumbnail',  # Embed thumbnail in MP3
                '--convert-thumbnails', 'jpg',  # Convert thumbnail to jpg
                '--restrict-filenames',  # Restrict filenames to ASCII characters
                '--format-sort', 'audio_only',  # Prefer audio-only formats
                '-o', '%(id)s.%(ext)s',  # Use only video ID for filename
                url
            ]

            self.current_process = await asyncio.create_subprocess_exec(
                *download_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.downloads_dir  # Set working directory to downloads
            )

            # Process stdout in real-time for progress updates
            while True:
                if view and view.cancelled:
                    if self.current_process and hasattr(self.current_process, 'terminate'):
                        try:
                            self.current_process.terminate()
                        except:
                            pass
                    self.current_process = None
                    if os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                            print(f"Cleaned up cancelled download: {output_file}")
                        except Exception as e:
                            print(f"Error cleaning up file: {str(e)}")
                    return None

                try:
                    line = await self.current_process.stdout.readline()
                    if not line:
                        break
                        
                    # Parse progress information
                    try:
                        line = line.decode().strip()
                        if line:
                            parts = line.split()
                            if len(parts) >= 3:
                                downloaded = int(parts[0])
                                total = int(parts[1])
                                speed = float(parts[2])
                                
                                await progress.progress_hook({
                                    'status': 'downloading',
                                    'downloaded_bytes': downloaded,
                                    'total_bytes': total,
                                    'speed': speed
                                })
                    except:
                        pass
                        
                except Exception as e:
                    print(f"Error reading progress: {str(e)}")
                    break

            # Wait for process to complete
            await self.current_process.wait()

            if self.current_process.returncode != 0:
                stderr = await self.current_process.stderr.read()
                error_msg = stderr.decode().strip()
                print(f"Error downloading video: {error_msg}")
                # Clean up failed download
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except:
                        pass
                raise Exception(f"Failed to download video: {error_msg}")

            if not os.path.exists(output_file):
                raise Exception("Download completed but file not found")

            # Update with completion message and store the message
            if status_msg:
                embed = discord.Embed(
                    title="Download Complete",
                    description=f"Successfully downloaded: [🎵 {title}]({url})",
                    color=0x2ecc71
                )
                await status_msg.edit(embed=embed)
                return {
                    'title': title,
                    'url': url,
                    'file_path': output_file,
                    'thumbnail': thumbnail,
                    'status_message': status_msg  # Store the status message
                }
            else:
                return {
                    'title': title,
                    'url': url,
                    'file_path': output_file,
                    'thumbnail': thumbnail
                }

        except Exception as e:
            if not (view and view.cancelled):  # Only show error if not cancelled
                print(f"Error in _download_single_video: {str(e)}")
                # Clean up on error
                if output_file and os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except:
                        pass
            raise

    async def after_playing_coro(self, error, ctx):
        """Coroutine called after a song finishes playing"""
        if error:
            print(f"Error in playback: {error}")
            embed = self.create_embed("Error", f"An error occurred during playback: {str(error)}", color=0xe74c3c)
            await ctx.send(embed=embed)  # Send as new message
        
        print("Song finished playing, checking queue...")
        if len(self.queue) > 0:
            print(f"Queue length: {len(self.queue)}")
        if not self.download_queue.empty():
            print(f"Download queue size: {self.download_queue.qsize()}")
        
        # If loop mode is enabled and we have a current song, add it back to the start of the queue
        if self.loop_mode and self.current_song:
            # Create a copy of the current song to preserve all attributes
            looped_song = self.current_song.copy()
            # Ensure has_played is set to True for the looped song
            looped_song['has_played'] = True
            self.queue.insert(0, looped_song)
            print("Loop mode: Added current song back to queue")
        
        # Start processing more downloads if needed
        if not self.currently_downloading and not self.download_queue.empty():
            print("More songs in download queue, continuing processing...")
        
        # If queue is empty but we're still downloading, wait briefly
        if len(self.queue) == 0 and not self.download_queue.empty():
            print("Waiting for next song to finish downloading...")
            await asyncio.sleep(1)  # Give a moment for download to complete
            
        if len(self.queue) > 0 or not self.download_queue.empty():
            await self.play_next(ctx)
        else:
            print("All songs finished, updating activity...")
            self.update_activity()
            if self.download_queue.empty():  # Only disconnect if nothing left to download
                if self.voice_client and self.voice_client.is_connected():
                    await self.voice_client.disconnect()

    def update_activity(self):
        """Update the last activity timestamp and bot status"""
        self.last_activity = time.time()
        
        async def set_activity():
            if self.current_song and (self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused())):
                # If a song is playing/paused, show it in the status
                status = f" [🎵 {self.current_song['title']}]({self.current_song['url']})"
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

    async def queue(self, ctx):
        """Show the current queue"""
        if not self.queue and self.download_queue.empty():
            await ctx.send(embed=self.create_embed("Queue Empty", "No songs in queue", color=0xe74c3c))
            return

        # Create queue message
        queue_text = ""
        position = 1

        # Add currently playing song
        if self.current_song:
            queue_text += "**Now Playing:**\n"
            queue_text += f"🎵 [{self.current_song['title']}]({self.current_song['url']})\n\n"

        # Add songs in queue
        if self.queue:
            queue_text += "**Up Next:**\n"
            for song in self.queue:
                queue_text += f"`{position}.` [{song['title']}]({song['url']})\n"
                position += 1

        # Add downloading songs
        if not self.download_queue.empty():
            queue_text += "\n**Downloading:**\n"
            downloading_count = self.download_queue.qsize()
            queue_text += f"🔄 {downloading_count} song(s) in download queue\n"

        # Create and send embed
        embed = self.create_embed(
            f"Music Queue - {len(self.queue)} song(s)",
            queue_text if queue_text else "Queue is empty",
            color=0x3498db
        )
        await ctx.send(embed=embed)

# Global variable for music bot instance
music_bot = None

def restart_bot():
    """Restart the bot by starting a new process and terminating the current one"""
    try:
        python = sys.executable
        script_path = os.path.abspath(__file__)
        cwd = os.getcwd()  # Get current working directory
        
        # Use subprocess instead of os.execl for better process handling
        import subprocess
        subprocess.Popen([python, script_path], cwd=cwd)
        os._exit(0)  # Exit the current process
    except Exception as e:
        print(f"Error during restart: {str(e)}")
        os._exit(1)  # Exit with error code if restart fails

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    global music_bot
    
    print(f"Logged in as {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    print("------")
    
    # Initialize the music bot
    if not music_bot:
        music_bot = MusicBot()
        await music_bot.setup(bot.loop)
        
        # Start the daily restart checker
        check_restart_time.start()
        print("Daily restart checker started")

@bot.command(name='play')
async def play(ctx, *, query):
    """Download and play a song from YouTube"""
    try:
        if not music_bot:
            raise Exception("Music bot not initialized")

        # Start the command processor if it's not running
        await music_bot.start_command_processor()

        # Add the command to the queue
        print(f"Adding command to queue: !play {query}")
        await music_bot.command_queue.put((ctx, query))

    except Exception as e:
        print(f"Error queueing play command: {e}")
        embed = music_bot.create_embed("Error", f"Failed to queue command: {str(e)}", color=0xe74c3c)
        await ctx.send(embed=embed)

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
                    f"[🎵 {music_bot.current_song['title']}]({music_bot.current_song['url']})",
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
                    f"[🎵 {music_bot.current_song['title']}]({music_bot.current_song['url']})",
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

@bot.command(name='queue', aliases=['playing'])
async def queue(ctx):
    """Show the current queue"""
    if not music_bot.queue and music_bot.download_queue.empty():
        await ctx.send(embed=music_bot.create_embed("Queue Empty", "No songs in queue", color=0xe74c3c))
        return

    # Create queue message
    queue_text = ""
    position = 1

    # Add currently playing song
    if music_bot.current_song:
        queue_text += "**Now Playing:**\n"
        queue_text += f"🎵 [{music_bot.current_song['title']}]({music_bot.current_song['url']})\n\n"

    # Add songs in queue
    if music_bot.queue:
        queue_text += "**Up Next:**\n"
        for song in music_bot.queue:
            queue_text += f"`{position}.` [{song['title']}]({song['url']})\n"
            position += 1

    # Add downloading songs
    if not music_bot.download_queue.empty():
        queue_text += "\n**Downloading:**\n"
        downloading_count = music_bot.download_queue.qsize()
        queue_text += f"🔄 {downloading_count} song(s) in download queue\n"

    # Create and send embed
    embed = music_bot.create_embed(
        f"Music Queue - {len(music_bot.queue)} song(s)",
        queue_text if queue_text else "Queue is empty",
        color=0x3498db
    )
    await ctx.send(embed=embed)

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

@bot.command(name='loop', aliases=['repeat'])
async def loop(ctx):
    """Toggle loop mode for the current song"""
    if not music_bot.current_song:
        await ctx.send(
            embed=music_bot.create_embed(
                "Error",
                "No song is currently playing!",
                color=0xe74c3c
            )
        )
        return

    # Toggle loop mode
    music_bot.loop_mode = not music_bot.loop_mode
    
    # Send status message
    status = "enabled" if music_bot.loop_mode else "disabled"
    color = 0x2ecc71 if music_bot.loop_mode else 0xe74c3c
    
    await ctx.send(
        embed=music_bot.create_embed(
            f"Loop Mode {status.title()}",
            f"[🎵 {music_bot.current_song['title']}]({music_bot.current_song['url']}) will {'now' if music_bot.loop_mode else 'no longer'} be looped",
            color=color
        )
    )

@bot.command(name='restart')
async def restart(ctx):
    """Restart the bot (Owner only)"""
    if ctx.author.id != OWNER_ID:
        await ctx.send(embed=discord.Embed(title="Error", description="Only the bot owner can use this command!", color=0xe74c3c))
        return

    await ctx.send(embed=discord.Embed(title="Restarting", description="Bot is restarting...", color=0xf1c40f))
    
    try:
        # Clear the downloads folder before restarting
        clear_downloads_folder()
        
        # Disconnect from voice if connected
        if music_bot and music_bot.voice_client:
            await music_bot.voice_client.disconnect()
        
        # Schedule the restart
        await bot.close()
        restart_bot()
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"Failed to restart: {str(e)}", color=0xe74c3c))

@tasks.loop(minutes=1)
async def check_restart_time():
    """Check if it's time for daily restart"""
    # Convert current time to EST
    est_time = datetime.now(pytz.timezone('America/New_York'))
    
    # Check if it's 3 AM EST
    if est_time.hour == RESTART_HOUR and est_time.minute == 0:
        print(f"It's {RESTART_HOUR}:00 AM EST - initiating scheduled restart")
        await auto_restart()

async def auto_restart():
    """Perform the restart operation"""
    print("Performing scheduled restart...")
    try:
        # Clear the downloads folder before restarting
        clear_downloads_folder()
        
        # Disconnect from voice if connected
        if music_bot and music_bot.voice_client:
            await music_bot.voice_client.disconnect()
        
        # Schedule the restart
        await bot.close()
        restart_bot()
    except Exception as e:
        print(f"Error during scheduled restart: {str(e)}")

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN'))
