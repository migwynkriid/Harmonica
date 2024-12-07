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
bot = commands.Bot(command_prefix='!', intents=intents)

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
        self.voice_client = None
        self.queue = []
        self.current_song = None
        self.last_activity = time.time()
        self.inactivity_timeout = 1800  # 30 minutes in seconds
        self._inactivity_task = None
        self.download_queue = []  # Queue for tracks to be downloaded
        self.currently_downloading = False  # Flag to track download status
        self.current_process = None  # Track current download process
        self.status_messages = {}  # Track status messages for each song
        self.current_command_msg = None  # Track the current command's message
        self.current_command_author = None  # Track the current command's author

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
        self.download_queue = []

    async def join_voice_channel(self, ctx):
        """Join the voice channel of the command author"""
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
                self.current_song = self.queue.pop(0)
                print(f"Playing next song: {self.current_song['title']}")
                print(f"Remaining songs in queue: {len(self.queue)}")
                print(f"Songs still downloading: {len(self.download_queue)}")
                
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

                async def after_playing_coro(error):
                    if error:
                        print(f"Error in playback: {error}")
                        embed = self.create_embed("Error", f"An error occurred during playback: {str(error)}", color=0xe74c3c)
                        await self.update_or_send_message(ctx, embed)
                    
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
                        await self.play_next(ctx)
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
                
                # Update now playing message
                await self.update_or_send_message(
                    ctx,
                    self.create_embed(
                        "Now Playing",
                        f"[{self.current_song['title']}]({self.current_song['url']})",
                        color=0x2ecc71,
                        thumbnail_url=self.current_song.get('thumbnail')
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
                        await self.play_next(ctx)
                    
                    # Start background download of next songs
                    asyncio.create_task(self.process_download_queue(ctx))
                    
                except Exception as e:
                    print(f"Error downloading song: {str(e)}")
                    self.download_queue.pop(0)  # Remove failed entry
                    
        finally:
            self.currently_downloading = False

    async def download_song(self, query, status_msg=None, view=None):
        """Download a song from YouTube"""
        try:
            # Check if the query is a URL
            is_url = query.startswith(('http://', 'https://', 'www.'))
            
            # If not a URL, treat as a search query
            if not is_url:
                query = f"ytsearch:{query}"
            
            print(f"Processing query: {query}")
            
            # Get video info first
            info_cmd = [
                'yt-dlp',
                '--print-json',
                '--flat-playlist',
                '--write-thumbnail',  # Get thumbnail info
                '--cookies', '../cookies.txt',  # Relative path since we're in downloads dir
                query
            ]
            
            # Execute yt-dlp command to get video/playlist info
            self.current_process = await asyncio.create_subprocess_exec(
                *info_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=DOWNLOADS_DIR  # Set working directory for info command too
            )

            # Check if cancelled
            if view and view.cancelled:
                self.current_process = None
                return None

            stdout, stderr = await self.current_process.communicate()
            
            if self.current_process.returncode != 0:
                error_msg = stderr.decode().strip()
                print(f"Error getting video info: {error_msg}")
                raise Exception(f"Failed to get video info: {error_msg}")
            
            # Parse the JSON output
            try:
                first_line = stdout.decode().strip().split('\n')[0]
                info = json.loads(first_line)
                
                # Get best thumbnail URL
                if 'thumbnails' in info:
                    thumbnails = info['thumbnails']
                    # Sort thumbnails by resolution if available
                    thumbnails.sort(key=lambda x: x.get('height', 0) * x.get('width', 0), reverse=True)
                    info['thumbnail'] = thumbnails[0]['url'] if thumbnails else None
                else:
                    info['thumbnail'] = None
                
                # Check if it's a playlist
                if info.get('_type') == 'playlist':
                    print("Playlist detected")
                    # For playlists, parse all entries
                    entries = []
                    for line in stdout.decode().strip().split('\n'):
                        entry_info = json.loads(line)
                        if entry_info.get('_type') != 'playlist':
                            entries.append(entry_info)
                    
                    return {
                        'is_playlist': True,
                        'entries': entries
                    }
                else:
                    # For single video or search result, download it
                    return await self._download_single_video(info, status_msg, view)
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {str(e)}")
                raise Exception(f"Failed to parse video info: {str(e)}")
                
        except Exception as e:
            print(f"Error in download_song: {str(e)}")
            raise

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
            output_file = os.path.join(DOWNLOADS_DIR, f"{video_id}.mp3")

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
                cwd=DOWNLOADS_DIR  # Set working directory to downloads
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
                    description=f"Successfully downloaded: {title}",
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

# Global variable for music bot instance
music_bot = None

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    global music_bot
    print(f"Logged in as {bot.user}")
    print('Clearing downloads folder...')
    clear_downloads_folder()
    print('Downloads folder cleared!')
    music_bot = MusicBot()
    await music_bot.start_inactivity_checker()

@bot.command(name='play')
async def play(ctx, *, query):
    """Download and play a song from YouTube"""
    try:
        music_bot.update_activity()
        
        # Create cancel button view
        cancel_view = CancelButton(music_bot)
        
        status_embed = music_bot.create_embed("Processing", "Processing your request...", color=0xf1c40f)
        # Force new message for new play command
        status_msg = await music_bot.update_or_send_message(ctx, status_embed, cancel_view, force_new=True)
        
        try:
            result = await music_bot.download_song(query, status_msg, cancel_view)
            
            # If cancelled, return early without error
            if cancel_view.cancelled:
                return
                
            # Remove the cancel button
            await music_bot.update_or_send_message(ctx, status_msg.embeds[0])
            
            # Handle playlist
            if isinstance(result, dict) and result.get('is_playlist'):
                if not await music_bot.join_voice_channel(ctx):
                    await music_bot.update_or_send_message(
                        ctx,
                        music_bot.create_embed(
                            "Error",
                            "Failed to join voice channel. Please make sure you're in a voice channel.",
                            color=0xe74c3c
                        )
                    )
                    return
                
                playlist_length = len(result['entries'])
                await music_bot.update_or_send_message(
                    ctx,
                    music_bot.create_embed(
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
                        await music_bot.play_next(ctx)
                    
                    # Start background download of next songs
                    asyncio.create_task(music_bot.process_download_queue(ctx))
                    
                    await music_bot.update_or_send_message(
                        ctx,
                        music_bot.create_embed(
                            "Playlist Started",
                            f"Playing first song. {playlist_length - 1} more songs will be processed in the background.",
                            color=0x2ecc71
                        )
                    )
                    
                except Exception as e:
                    print(f"Error starting playlist: {str(e)}")
                    await music_bot.update_or_send_message(
                        ctx,
                        music_bot.create_embed(
                            "Error",
                            f"An error occurred while starting the playlist: {str(e)}",
                            color=0xe74c3c
                        )
                    )
            
            # Handle single video
            else:
                if not await music_bot.join_voice_channel(ctx):
                    await music_bot.update_or_send_message(
                        ctx,
                        music_bot.create_embed(
                            "Error",
                            "Failed to join voice channel. Please make sure you're in a voice channel.",
                            color=0xe74c3c
                        )
                    )
                    return
        
                if music_bot.voice_client and music_bot.voice_client.is_playing():
                    music_bot.queue.append(result)
                    await music_bot.update_or_send_message(
                        ctx,
                        music_bot.create_embed(
                            "Added to Queue",
                            f"[{result['title']}]({result['url']})",
                            color=0x3498db,
                            thumbnail_url=result.get('thumbnail')
                        )
                    )
                else:
                    music_bot.queue.append(result)
                    await music_bot.play_next(ctx)
                
        except Exception as e:
            if not cancel_view.cancelled:  # Only show error if not cancelled
                error_embed = music_bot.create_embed("Error", f"An error occurred: {str(e)}", color=0xe74c3c)
                await music_bot.update_or_send_message(ctx, error_embed)
            return
            
    except Exception as e:
        if not cancel_view.cancelled:  # Only show error if not cancelled
            print(f"Error in play command: {str(e)}")
            await music_bot.update_or_send_message(
                ctx,
                music_bot.create_embed(
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
