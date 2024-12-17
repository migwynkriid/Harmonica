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
from pytz import timezone
import pytz
import logging
import urllib.request
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Function to download yt-dlp based on platform
def ensure_ytdlp():
    try:
        if sys.platform.startswith('win'):
            ytdlp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yt-dlp.exe')
            if not os.path.exists(ytdlp_path):
                print("Downloading yt-dlp.exe...")
                url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp.exe"
                urllib.request.urlretrieve(url, ytdlp_path)
                os.chmod(ytdlp_path, 0o755)  # Make executable
                print("yt-dlp.exe downloaded successfully")
            return ytdlp_path
        elif sys.platform.startswith('darwin'):  # macOS
            ytdlp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yt-dlp')
            if not os.path.exists(ytdlp_path):
                print("Downloading yt-dlp for macOS...")
                url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp_macos"
                urllib.request.urlretrieve(url, ytdlp_path)
                os.chmod(ytdlp_path, 0o755)  # Make executable
                print("yt-dlp downloaded successfully")
            return ytdlp_path
        else:  # Linux
            ytdlp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yt-dlp')
            if not os.path.exists(ytdlp_path):
                print("Downloading yt-dlp for Linux...")
                
                # Get machine architecture
                import platform
                machine = platform.machine().lower()
                
                # Select appropriate URL based on architecture
                if machine in ['aarch64', 'arm64']:
                    url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp_linux_aarch64"
                elif machine == 'armv7l':
                    url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp_linux_armv7l"
                else:  # x86_64, amd64, etc.
                    url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp_linux"
                
                print(f"Detected architecture: {machine}, downloading appropriate version...")
                urllib.request.urlretrieve(url, ytdlp_path)
                os.chmod(ytdlp_path, 0o755)  # Make executable
                print("yt-dlp downloaded successfully")
            return ytdlp_path
    except Exception as e:
        print(f"Error downloading yt-dlp: {str(e)}")
        return None

def check_ffmpeg_in_path():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_ffmpeg_windows():
    try:
        print("FFmpeg not found. Installing FFmpeg using winget...")
        subprocess.run(['winget', 'install', 'FFmpeg (Essentials Build)'], check=True)
        print("FFmpeg installed successfully. Please restart the bot for changes to take effect.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing FFmpeg: {e}")
        return False

def install_ffmpeg_macos():
    try:
        # First try with Homebrew
        print("FFmpeg not found. Attempting to install FFmpeg using Homebrew...")
        try:
            subprocess.run(['brew', 'install', 'ffmpeg'], check=True)
            print("FFmpeg installed successfully using Homebrew. Please restart the bot for changes to take effect.")
            return True
        except subprocess.CalledProcessError:
            print("Homebrew installation failed. Trying MacPorts...")
            
            # If Homebrew fails, try MacPorts
            try:
                subprocess.run(['sudo', 'port', 'install', 'ffmpeg'], check=True)
                print("FFmpeg installed successfully using MacPorts. Please restart the bot for changes to take effect.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"MacPorts installation failed: {e}")
                return False
    except Exception as e:
        print(f"Error installing FFmpeg: {e}")
        return False

def install_ffmpeg_linux():
    try:
        print("FFmpeg not found. Installing FFmpeg using apt...")
        subprocess.run(['sudo', 'apt', 'install', 'ffmpeg', '-y'], check=True)
        print("FFmpeg installed successfully. Please restart the bot for changes to take effect.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing FFmpeg: {e}")
        return False

# Function to get appropriate ffmpeg path based on platform
def get_ffmpeg_path():
    if sys.platform.startswith('win'):
        # First check in root directory
        local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
        
        # Then check in PATH
        if check_ffmpeg_in_path():
            return 'ffmpeg'
        
        # If not found anywhere, try to install it
        if install_ffmpeg_windows():
            return 'ffmpeg'
        else:
            print("WARNING: FFmpeg not found and installation failed. Please install FFmpeg manually.")
            return 'ffmpeg'  # Return ffmpeg anyway, it might be available after restart
    elif sys.platform.startswith('darwin'):  # macOS
        # First check in PATH
        if check_ffmpeg_in_path():
            return 'ffmpeg'
        
        # If not found, try to install it
        if install_ffmpeg_macos():
            return 'ffmpeg'
        else:
            print("WARNING: FFmpeg not found and installation failed. Please install FFmpeg manually using 'brew install ffmpeg' or 'sudo port install ffmpeg'")
            return 'ffmpeg'  # Return ffmpeg anyway, it might be available after restart
    else:  # Linux
        # First check in PATH
        if check_ffmpeg_in_path():
            return 'ffmpeg'
        
        # If not found, try to install it
        if install_ffmpeg_linux():
            return 'ffmpeg'
        else:
            print("WARNING: FFmpeg not found and installation failed. Please install FFmpeg manually using 'sudo apt install ffmpeg'")
            return 'ffmpeg'  # Return ffmpeg anyway, it might be available after restart

# Function to get yt-dlp path, prioritizing local over global
def get_ytdlp_path():
    local_path = os.path.join(os.getcwd(), 'yt-dlp')
    if os.path.exists(local_path):
        return local_path
    return 'yt-dlp'  # Fallback to global yt-dlp

# Download and set up yt-dlp
YTDLP_PATH = ensure_ytdlp()
FFMPEG_PATH = get_ffmpeg_path()

# Set up logging to capture all output
file_handler = logging.FileHandler('log.txt', encoding='utf-8')
console_handler = logging.StreamHandler(sys.stdout)

# Configure root logger to capture all logs
logging.basicConfig(
    level=logging.DEBUG,  # Capture all levels of logs
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[file_handler, console_handler]
)

# Set logging level for specific libraries
logging.getLogger('discord').setLevel(logging.DEBUG)  # Capture all discord logs
logging.getLogger('yt-dlp').setLevel(logging.DEBUG)    # Capture all yt-dlp logs

# Optionally suppress specific loggers if needed
logging.getLogger('discord.player').setLevel(logging.WARNING)  # Suppress player logs if desired

# Configure logging to suppress the ffmpeg process termination message
logging.getLogger('discord.player').setLevel(logging.WARNING)

# Force UTF-8 globally
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Load Spotify credentials
load_dotenv(dotenv_path=".spotifyenv")

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
OWNER_ID = 220301180562046977

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

# Initialize Spotipy client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv('SPOTIPY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIPY_CLIENT_SECRET')
))

# Function to extract Spotify track details
async def get_spotify_track_details(spotify_url):
    try:
        if 'track/' in spotify_url:
            track_id = spotify_url.split('track/')[-1].split('?')[0]
            track_info = sp.track(track_id)
            artist_name = track_info['artists'][0]['name']
            track_name = track_info['name']
            return f"{artist_name} - {track_name}"
        # Add handling for album and playlist if needed
    except Exception as e:
        print(f"Error retrieving Spotify track details: {str(e)}")
        return None

async def get_spotify_album_details(spotify_url):
    try:
        if 'album/' in spotify_url:
            album_id = spotify_url.split('album/')[-1].split('?')[0]
            album_info = sp.album_tracks(album_id)
            tracks = [f"{track['artists'][0]['name']} - {track['name']}" for track in album_info['items']]
            return tracks
    except Exception as e:
        print(f"Error retrieving Spotify album details: {str(e)}")
        return []

async def get_spotify_playlist_details(spotify_url):
    try:
        if 'playlist/' in spotify_url:
            playlist_id = spotify_url.split('playlist/')[-1].split('?')[0]
            playlist_info = sp.playlist_tracks(playlist_id)
            tracks = [f"{track['track']['artists'][0]['name']} - {track['track']['name']}" for track in playlist_info['items']]
            return tracks
    except Exception as e:
        print(f"Error retrieving Spotify playlist details: {str(e)}")
        return []

# Global error handler for command errors
@bot.event
async def on_command_error(ctx, error):
    # Log the error to the console
    print(f"Error in command {ctx.command}: {str(error)}")
    # Send error message to the Discord chat
    await ctx.send(
        embed=music_bot.create_embed(
            "Error",
            f"Error: {str(error)}",
            color=0xe74c3c
        )
    )

# Add error handler for CommandNotFound
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Silently ignore command not found errors
    # For other errors, print them to the console
    print(f"Error: {str(error)}")

# Add voice state update handler
@bot.event
async def on_voice_state_update(member, before, after):
    global music_bot
    if not music_bot or not music_bot.voice_client:
        return

    # Get the voice channel the bot is in
    bot_voice_channel = music_bot.voice_client.channel
    if not bot_voice_channel:
        return

    # Count members in the channel (excluding bots)
    members_in_channel = sum(1 for m in bot_voice_channel.members if not m.bot)

    # If no human members in the channel, disconnect the bot
    if members_in_channel == 0:
        print(f"No users in voice channel {bot_voice_channel.name}, disconnecting bot")
        await music_bot.leave_voice_channel()
        
# YouTube DL options
YTDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a][abr<=96]/bestaudio[abr<=96]/bestaudio/best/bestaudio*',  # More flexible format selection with fallbacks
    'outtmpl': '%(id)s.%(ext)s',
    'extract_audio': True,
    'concurrent_fragments': 4,
    'abort_on_unavailable_fragments': True,
    'nopostoverwrites': True,
    'windowsfilenames': True,
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'extract_flat': False,
    'force_generic_extractor': False,
    'verbose': True,
    'logger': logging.getLogger('yt-dlp'),
    'ignoreerrors': True,
    'ffmpeg_location': FFMPEG_PATH,  # Use platform-specific ffmpeg path
    'yt_dlp_filename': get_ytdlp_path()
}

# FFmpeg options (simplified, only used for streaming)
FFMPEG_OPTIONS = {
    'executable': FFMPEG_PATH,  # Use platform-specific ffmpeg path
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}

class CancelButton(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot = bot_instance
        self.cancelled = False
        self.current_file = None

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
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
        filled = int(width * (percentage / 100))
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
        # Queue and playback related
        self.queue = []  # Queue of songs to play
        self.current_song = None  # Currently playing song
        self.is_playing = False  # Flag to track if bot is currently playing
        self.voice_client = None  # Voice client instance
        self.loop_mode = False  # Flag to track if loop mode is enabled
        self.waiting_for_song = False  # Flag to track if waiting for a song to be ready
        
        # Async related
        self.queue_lock = asyncio.Lock()  # Lock for queue operations
        self.download_queue = asyncio.Queue()  # Queue for background downloads
        self.currently_downloading = False  # Flag to track if currently downloading
        self.command_queue = asyncio.Queue()  # Queue for play commands
        self.command_processor_task = None  # Task for processing commands
        self.download_lock = asyncio.Lock()  # Lock for download synchronization
        self.bot_loop = None  # Store bot's event loop
        
        # Message tracking
        self.queued_messages = {}  # Store messages for each queued song
        self.current_command_msg = None  # Store the current command message
        self.current_command_author = None  # Store the current command author
        self.status_messages = {}  # Track status messages
        self.now_playing_message = None  # Track Now Playing message
        
        # File system related
        self.downloads_dir = os.path.join(os.getcwd(), 'downloads')  # Directory for downloaded files
        self.cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
        
        # Create downloads directory if it doesn't exist
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)

        # Activity tracking
        self.last_activity = time.time()
        self.inactivity_timeout = 900  # 15 minutes in seconds
        self._inactivity_task = None
        self.last_update = 0
        self._last_progress = -1
        self.last_known_ctx = None
        self.bot = None

        # Initialize Spotify client
        load_dotenv('.spotifyenv')
        client_id = os.getenv('SPOTIPY_CLIENT_ID')
        client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        
        print(f"Spotify environment file path: {os.path.abspath('.spotifyenv')}")
        print(f"Spotify client ID found: {'Yes' if client_id else 'No'}")
        print(f"Spotify client secret found: {'Yes' if client_secret else 'No'}")
        
        if not client_id or not client_secret:
            print("Warning: Spotify credentials not found. Spotify functionality will be limited.")
            self.sp = None
        else:
            try:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=client_id,
                    client_secret=client_secret
                )
                self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
                print("Successfully initialized Spotify client")
            except Exception as e:
                print(f"Error initializing Spotify client: {str(e)}")
                self.sp = None

    async def setup(self, bot_instance):
        """Setup the bot with the event loop"""
        self.bot = bot_instance
        self.bot_loop = asyncio.get_event_loop()
        await self.start_command_processor()
        await self.start_inactivity_checker()
        asyncio.create_task(self.process_download_queue())
        print("Command processor started")

    async def start_command_processor(self):
        """Start the command processor task"""
        if self.command_processor_task is None:
            self.command_processor_task = asyncio.create_task(self.process_command_queue())
            print("Command processor started")

    async def process_command_queue(self):
        """Process commands from the queue one at a time"""
        while True:
            try:
                # Wait for the next command
                command_info = await self.command_queue.get()
                self.last_activity = time.time()  # Update activity when processing commands
                
                # Get the next command from the queue
                ctx, query = command_info
                
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

        self.last_activity = time.time()  # Update activity when handling play command
        
        # Send initial status message
        processing_embed = self.create_embed(
            "Processing",
            f"Processing request: {query}",
            color=0x3498db
        )
        status_msg = await self.update_or_send_message(ctx, processing_embed)

        # Create download info
        download_info = {
            'query': query,
            'ctx': ctx,
            'status_msg': status_msg
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

                try:
                    async with self.download_lock:  # Ensure only one download at a time
                        self.currently_downloading = True
                        print(f"Starting download: {query}")
                        
                        # Download the song
                        result = await self.download_song(query, status_msg=status_msg, ctx=ctx)
                        
                        if not result:
                            if not status_msg:
                                error_embed = self.create_embed("Error", "Failed to download song", color=0xe74c3c)
                                await self.update_or_send_message(ctx, error_embed)
                            continue

                        # Only delete status message if it's not a playlist message
                        if status_msg and not result.get('is_from_playlist'):
                            try:
                                message_exists = True
                                try:
                                    await status_msg.fetch()
                                except discord.NotFound:
                                    message_exists = False
                                
                                if message_exists:
                                    await status_msg.delete()
                            except Exception as e:
                                print(f"Note: Could not delete processing message: {e}")
                                # Continue execution even if message deletion fails
                        else:
                            # For playlists, update the status message to show playlist info
                            if status_msg:
                                playlist_embed = self.create_embed(
                                    "Adding Playlist",
                                    f"Adding {len(result['entries'])} songs to queue...",
                                    color=0x3498db
                                )
                                await status_msg.edit(embed=playlist_embed)

                        # Add to queue or play immediately
                        if self.voice_client and self.voice_client.is_playing():
                            self.queue.append(result)
                            # Only show "Added to Queue" for non-playlist items
                            if not result.get('is_from_playlist'):
                                queue_embed = self.create_embed(
                                    "Added to Queue", 
                                    f"[🎵 {result['title']}]({result['url']})",
                                    color=0x3498db,
                                    thumbnail_url=result.get('thumbnail')
                                )
                                queue_msg = await ctx.send(embed=queue_embed)
                                # Store the queue message
                                self.queued_messages[result['url']] = queue_msg
                        else:
                            self.queue.append(result)
                            await self.play_next(ctx)  # Always show Now Playing

                except Exception as e:
                    print(f"Error processing download: {str(e)}")
                    if not status_msg:
                        error_embed = self.create_embed("Error", f"Error processing: {str(e)}", color=0xe74c3c)
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
            self._inactivity_task = self.bot_loop.create_task(self.check_inactivity())
        except Exception as e:
            print(f"Error starting inactivity checker: {str(e)}")

    async def check_inactivity(self):
        """Check for inactivity and leave voice if inactive too long"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                if self.voice_client and self.voice_client.is_connected():
                    # If music is playing, update activity
                    if self.voice_client.is_playing():
                        self.last_activity = time.time()
                    # If not playing and inactive for too long
                    elif time.time() - self.last_activity > self.inactivity_timeout:
                        print(f"Leaving voice channel due to {self.inactivity_timeout} seconds of inactivity")
                        await self.leave_voice_channel()
                        self.clear_queue()
            except Exception as e:
                print(f"Error in inactivity checker: {str(e)}")
                await asyncio.sleep(60)  # Still wait before next check even if there's an error

    def clear_queue(self):
        """Clear both download and playback queues"""
        try:
            # Clear the playback queue
            self.queue.clear()
            
            # Clear the download queue
            items_removed = 0
            while not self.download_queue.empty():
                try:
                    self.download_queue.get_nowait()
                    items_removed += 1
                except asyncio.QueueEmpty:
                    break
            
            # Only call task_done() for items we actually removed
            for _ in range(items_removed):
                try:
                    self.download_queue.task_done()
                except ValueError:
                    # If we get a ValueError, the queue is already empty
                    break
            
            # Cancel any ongoing downloads
            if self.current_process:
                try:
                    self.current_process.kill()
                except:
                    pass
                self.current_process = None

            # Stop any currently playing audio
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.stop()
                # Give FFmpeg a moment to clean up
                time.sleep(0.5)

        except Exception as e:
            print(f"Error clearing queue: {str(e)}")

    async def stop(self, ctx):
        """Stop playing and clear the queue"""
        try:
            # Stop any currently playing audio and reset voice state
            if self.voice_client:
                if self.voice_client.is_playing():
                    self.voice_client.stop()
                    # Give FFmpeg a moment to clean up
                    await asyncio.sleep(0.5)
                # Disconnect and reset voice client
                await self.voice_client.disconnect()

            # Clear the queue
            self.clear_queue()
            self.current_song = None
            
            # Reset the bot's status
            await self.bot.change_presence(activity=discord.Game(name="nothing! use !play "))
            
            # Send confirmation message
            await ctx.send(embed=self.create_embed("Stopped", "Music stopped and queue cleared", color=0xe74c3c))

        except Exception as e:
            print(f"Error in stop command: {str(e)}")
            await ctx.send(embed=self.create_embed("Error", "Failed to stop playback", color=0xe74c3c))

    async def join_voice_channel(self, ctx):
        """Join the user's voice channel"""
        if not ctx.author.voice:
            await ctx.send(embed=self.create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c))
            return False

        try:
            channel = ctx.author.voice.channel
            
            # Always disconnect and reset if we have an existing voice client
            if self.voice_client:
                try:
                    if self.voice_client.is_connected():
                        await self.voice_client.disconnect(force=True)
                except:
                    pass
                self.voice_client = None

            # Create new connection
            self.voice_client = await channel.connect(self_deaf=True)
            self.last_activity = time.time()  # Update activity when joining channel
            return self.voice_client.is_connected()

        except Exception as e:
            print(f"Error joining voice channel: {str(e)}")
            await ctx.send(embed=self.create_embed("Error", "Failed to join voice channel!", color=0xe74c3c))
            # Reset voice client if connection failed
            self.voice_client = None
            return False

    async def leave_voice_channel(self):
        """Leave voice channel and cleanup"""
        try:
            if self.voice_client:
                if self.voice_client.is_playing():
                    self.voice_client.stop()
                if self.voice_client.is_connected():
                    await self.voice_client.disconnect(force=True)
        except Exception as e:
            print(f"Error leaving voice channel: {str(e)}")
        finally:
            # Always reset voice client state
            self.voice_client = None
            self.current_song = None

    async def play_next(self, ctx):
        """Play the next song in the queue"""
        if len(self.queue) > 0:
            try:
                # Store previous song for comparison
                previous_song = self.current_song
                self.current_song = self.queue.pop(0)  # Remove the song immediately when we start processing it
                self.last_activity = time.time()  # Update activity when starting new song
                print(f"Playing next song: {self.current_song['title']}")
                
                # For radio streams, we don't need to check if the file exists
                if not self.current_song.get('is_stream'):
                    if not os.path.exists(self.current_song['file_path']):
                        print(f"Error: File not found: {self.current_song['file_path']}")
                        if len(self.queue) > 0:
                            await self.play_next(ctx)
                        return

                # Ensure we're in a voice channel
                if not self.voice_client or not self.voice_client.is_connected():
                    print("Voice client not connected, attempting to reconnect...")
                    connected = await self.join_voice_channel(ctx)
                    if not connected:
                        print("Failed to reconnect to voice channel")
                        self.voice_client = None
                        
                        # Automatically restart the bot if voice connection fails
                        try:
                            await ctx.send("⚠️ Internal error detected!. Automatically restarting bot...")
                            await restart(ctx)
                        except Exception as e:
                            print(f"Error during automatic restart in play_next: {str(e)}")
                        return
                else:
                    # If there's a previous Now Playing message, update it to Finished Playing
                    if self.now_playing_message:
                        try:
                            finished_embed = self.create_embed(
                                "Finished Playing",
                                f"[🎵 {previous_song['title']}]({previous_song['url']})",
                                color=0x808080,  # Gray color for finished
                                thumbnail_url=previous_song.get('thumbnail')
                            )
                            await self.now_playing_message.edit(embed=finished_embed)
                        except Exception as e:
                            print(f"Error updating previous now playing message: {str(e)}")

                    # Send Now Playing message and store it
                    now_playing_embed = self.create_embed(
                        "Now Playing",
                        f"[🎵 {self.current_song['title']}]({self.current_song['url']})",
                        color=0x00ff00,
                        thumbnail_url=self.current_song.get('thumbnail')
                    )
                    self.now_playing_message = await ctx.send(embed=now_playing_embed)
                    
                    # Update bot's activity to show current song
                    await self.bot.change_presence(activity=discord.Game(name=f"{self.current_song['title']}"))
                    
                    # Reset current message tracking for next command
                    self.current_command_msg = None
                    self.current_command_author = None

                    # Play the audio
                    try:
                        if self.voice_client and self.voice_client.is_connected():
                            # Add reconnect options for streams
                            ffmpeg_options = {
                                'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                            }
                            # For streams, use the URL directly
                            audio_source = discord.FFmpegPCMAudio(
                                self.current_song['file_path'],
                                **ffmpeg_options
                            )
                            self.voice_client.play(
                                audio_source,
                                after=lambda e: asyncio.run_coroutine_threadsafe(
                                    self.after_playing_coro(e, ctx), 
                                    self.bot_loop
                                )
                            )
                    except Exception as e:
                        print(f"Error starting playback: {str(e)}")
                        if len(self.queue) > 0:
                            await self.play_next(ctx)
            except Exception as e:
                print(f"Error in play_next: {str(e)}")
                if len(self.queue) > 0:
                    await self.play_next(ctx)
        else:
            self.current_song = None
            self.update_activity()
            # Reset activity when no more songs
            await self.bot.change_presence(activity=discord.Game(name="nothing! use !play "))
            if self.download_queue.empty():  # Only disconnect if nothing left to download
                if self.voice_client and self.voice_client.is_connected():
                    await self.voice_client.disconnect()

    async def process_queue(self):
        """Process the song queue"""
        if self.waiting_for_song or not self.queue:
            return

        self.waiting_for_song = True

        try:
            # Get and remove the next song from the queue
            song = self.queue.pop(0)  # Remove the song immediately when we start processing it
            
            # Get context from song info, or use the last known context if missing
            ctx = song.get('ctx')
            if not ctx:
                print("Warning: Missing context in song, using last known context")
                if hasattr(self, 'last_known_ctx'):
                    ctx = self.last_known_ctx
                else:
                    print("Error: No context available for playback")
                    self.waiting_for_song = False
                    if self.queue:  # Try next song if this one fails
                        await self.process_queue()
                    return

            # Store the context for future use
            self.last_known_ctx = ctx

            # Verify voice client connection
            if not self.voice_client or not self.voice_client.is_connected():
                print("Not connected to voice during process_queue")
                try:
                    # Attempt to send restart message
                    if ctx:
                        await ctx.send("⚠️ Voice connection lost. Automatically restarting bot...")
                    
                    # Trigger bot restart
                    await restart(ctx)
                except Exception as e:
                    print(f"Error during automatic restart in process_queue: {str(e)}")
                return

            # Delete the "Added to Queue" message if it exists
            if song['url'] in self.queued_messages:
                try:
                    await self.queued_messages[song['url']].delete()
                except Exception as e:
                    print(f"Error deleting queue message: {str(e)}")
                finally:
                    del self.queued_messages[song['url']]

            # Play the song
            self.current_song = song
            self.is_playing = True
            
            # Send Now Playing message and store it
            now_playing_embed = self.create_embed(
                "Now Playing",
                f"[🎵 {song['title']}]({song['url']})",
                color=0x00ff00,
                thumbnail_url=song.get('thumbnail')
            )
            self.now_playing_message = await ctx.send(embed=now_playing_embed)
            
            # Update bot's activity to show current song
            await self.bot.change_presence(activity=discord.Game(name=f"{song['title']}"))
            
            # Create FFmpeg audio source
            if song.get('is_stream'):
                # For radio streams, use the URL directly
                audio_source = discord.FFmpegPCMAudio(
                    song['file_path'],
                    **FFMPEG_OPTIONS
                )
            else:
                # For downloaded songs, use the file path
                audio_source = discord.FFmpegPCMAudio(
                    song['file_path'],
                    **FFMPEG_OPTIONS
                )

            # Add volume control
            audio_source = discord.PCMVolumeTransformer(audio_source, volume=0.75)

            # Store message and song info for after_playing
            current_message = self.now_playing_message
            current_song_info = {
                'title': song['title'],
                'url': song['url'],
                'thumbnail': song.get('thumbnail')
            }

            def after_playing(error):
                """Callback after song finishes"""
                if error:
                    print(f"Error in playback: {error}")
                
                # Update Now Playing to Finished Playing
                async def update_now_playing():
                    try:
                        if current_message:
                            finished_embed = self.create_embed(
                                "Finished Playing",
                                f"[{current_song_info['title']}]({current_song_info['url']})",
                                color=0x808080,  # Green color to indicate completion
                                thumbnail_url=current_song_info.get('thumbnail')
                            )
                            await current_message.edit(embed=finished_embed)
                            # Reset states after updating message
                            self.is_playing = False
                            self.waiting_for_song = False
                            self.current_song = None
                            self.now_playing_message = None
                            # Reset the bot's status and process next song
                            activity = discord.Game(name="nothing! use !play ")
                            await self.bot.change_presence(activity=activity)
                            await self.process_queue()
                    except Exception as e:
                        print(f"Error updating finished message: {str(e)}")
                
                # Schedule the message update
                asyncio.run_coroutine_threadsafe(update_now_playing(), self.bot_loop)

            # Start playing
            self.voice_client.play(audio_source, after=after_playing)

        except Exception as e:
            print(f"Error in process_queue: {str(e)}")
            if ctx:
                error_embed = self.create_embed("Error", f"Error playing song: {str(e)}", color=0xff0000)
                await ctx.send(embed=error_embed)

        finally:
            self.waiting_for_song = False
            if not self.is_playing:
                # If something went wrong and we're not playing, try next song
                await self.process_queue()

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
            self.current_command_author = ctx.author_id
            return self.current_command_msg

    def is_radio_stream(self, url):
        """Check if the URL is a radio stream"""
        # Common audio stream extensions
        stream_extensions = ['.mp3', '.aac', '.m4a', '.ogg', '.opus']
        return any(url.lower().endswith(ext) for ext in stream_extensions)

    def is_playlist_url(self, url):
        """Check if the URL is a YouTube playlist"""
        return 'youtube.com/playlist' in url.lower()

    def create_progress_bar(self, percentage, length=10):
        """Create a progress bar with the given percentage"""
        filled = int(length * (percentage / 100))
        bar = '█' * filled + '░' * (length - filled)
        return f"[{bar}] {percentage}%"

    def format_size(self, bytes):
        """Format bytes into human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} TB"

    async def progress_hook(self, d, status_msg):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            try:
                # Calculate percentage
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    downloaded = d.get('downloaded_bytes', 0)
                    percentage = int((downloaded / total) * 100)
                    
                    # Only update every 10%
                    if percentage % 10 == 0 and percentage != self._last_progress:
                        self._last_progress = percentage
                        progress_bar = self.create_progress_bar(percentage)
                        
                        # Format the total file size
                        total_size = self.format_size(total)
                        
                        # Try to fetch the message to see if it still exists
                        try:
                            await status_msg.fetch()  # This will raise NotFound if message is deleted
                            # Update the processing message with progress bar and file size
                            processing_embed = self.create_embed(
                                "Processing",
                                f"Downloading...\n{progress_bar}\nFile size: {total_size}",
                                color=0x3498db
                            )
                            await status_msg.edit(embed=processing_embed)
                        except discord.NotFound:
                            return
                        except Exception as e:
                            print(f"Error updating progress message: {str(e)}")
                            return
            except Exception as e:
                print(f"Error in progress hook: {str(e)}")

    def is_url(self, query):
        """Check if the query is a URL"""
        # Simple URL validation
        return query.startswith(('http://', 'https://', 'www.'))

    async def download_song(self, query, status_msg=None, ctx=None):
        """Download a song from YouTube, Spotify, or handle radio stream"""
        try:
            # Reset progress tracking
            self._last_progress = -1

            # Check if it's a YouTube playlist
            if self.is_playlist_url(query):
                # We need ctx for voice channel operations
                ctx = ctx or status_msg.channel if status_msg else None
                await self._handle_playlist(query, ctx, status_msg)
                return None

            # Check if the query is a Spotify URL
            if 'open.spotify.com/' in query:
                if 'track/' in query:
                    spotify_details = await get_spotify_track_details(query)
                    if spotify_details:
                        query = spotify_details
                    else:
                        if status_msg:
                            await status_msg.edit(
                                embed=self.create_embed(
                                    "Error",
                                    "Could not retrieve details from Spotify URL.",
                                    color=0xe74c3c
                                )
                            )
                        return None
                elif 'album/' in query:
                    tracks = await get_spotify_album_details(query)
                    first_song = None
                    for track in tracks:
                        print(f"Processing track: {track}")
                        song_info = await self.download_song(track, status_msg, ctx)
                        if song_info:
                            if not first_song:
                                first_song = song_info
                            else:
                                async with self.queue_lock:
                                    self.queue.append(song_info)
                                    print(f"Added to queue: {song_info['title']}")
                    return first_song
                elif 'playlist/' in query:
                    tracks = await get_spotify_playlist_details(query)
                    first_song = None
                    for track in tracks:
                        print(f"Processing track: {track}")
                        song_info = await self.download_song(track, status_msg, ctx)
                        if song_info:
                            if not first_song:
                                first_song = song_info
                            else:
                                async with self.queue_lock:
                                    self.queue.append(song_info)
                                    print(f"Added to queue: {song_info['title']}")
                    return first_song

            # If not a Spotify URL, proceed with existing yt-dlp logic
            # Check if the query is a radio stream URL
            if self.is_radio_stream(query):
                print("Radio stream detected")
                try:
                    # Get a name from the URL
                    stream_name = query.split('/')[-1].split('.')[0]
                    result = {
                        'title': stream_name,
                        'url': query,
                        'file_path': query,  # Use the URL directly as the file path for FFmpeg
                        'is_stream': True,
                        'thumbnail': None
                    }
                    # Remove the processing message since we don't need to show download progress for streams
                    if status_msg:
                        await status_msg.delete()
                    return result
                except Exception as e:
                    print(f"Error processing radio stream: {str(e)}")
                    if status_msg:
                        await status_msg.edit(
                            embed=self.create_embed(
                                "Error",
                                f"Failed to process radio stream: {str(e)}",
                                color=0xe74c3c
                            )
                        )
                    return None

            # Ensure downloads directory exists
            if not os.path.exists(self.downloads_dir):
                os.makedirs(self.downloads_dir)

            # If query is not a URL, treat it as a search query
            if not self.is_url(query):
                query = f"ytsearch:{query}"

            # Base yt-dlp options
            ydl_opts = {
                **YTDL_OPTIONS,  # Use base options
                'outtmpl': os.path.join(self.downloads_dir, '%(id)s.%(ext)s'),
                'cookiefile': self.cookie_file if os.path.exists(self.cookie_file) else None,
                'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(
                    self.progress_hook(d, status_msg), 
                    self.bot_loop
                )] if status_msg else [],
                'default_search': 'ytsearch'  # Enable YouTube search
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First extract info without downloading to check if it's a playlist
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                
                # Handle search results
                if info.get('_type') == 'playlist' and not self.is_playlist_url(query):
                    # This is a search result, get the first video
                    if not info.get('entries'):
                        raise Exception("No search results found")
                    info = info['entries'][0]
                    
                    # Download the actual video
                    video_info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(
                        info['webpage_url'],
                        download=True
                    ))
                    
                    # Sometimes yt-dlp returns a playlist format even for single videos
                    if video_info.get('_type') == 'playlist':
                        video_info = video_info['entries'][0]
                    
                    # Get the file path
                    file_path = os.path.join(self.downloads_dir, f"{video_info['id']}.{video_info.get('ext', 'opus')}")
                    
                    # Delete the processing message after successful download
                    if status_msg:
                        try:
                            message_exists = True
                            try:
                                await status_msg.fetch()
                            except discord.NotFound:
                                message_exists = False
                            
                            if message_exists:
                                await status_msg.delete()
                        except Exception as e:
                            print(f"Note: Could not delete processing message: {str(e)}")
                            # Continue execution even if message deletion fails
                    
                    # Return the song info
                    return {
                        'title': video_info['title'],
                        'url': video_info['webpage_url'] if video_info.get('webpage_url') else video_info['url'],
                        'file_path': file_path,
                        'thumbnail': video_info.get('thumbnail'),
                        'is_from_playlist': False,
                        'ctx': status_msg.channel if status_msg else None
                    }
                elif info.get('_type') == 'playlist' and self.is_playlist_url(query):
                    # It's a playlist, get the first video
                    if not info.get('entries'):
                        raise Exception("Playlist is empty")

                    # Get context from status message
                    ctx = ctx or status_msg.channel if status_msg else None

                    # Get first video info for thumbnail
                    first_video = info['entries'][0]
                    video_thumbnail = first_video.get('thumbnail')

                    # Update status message to show playlist info
                    playlist_title = info.get('title', 'Unknown Playlist')
                    playlist_url = info.get('webpage_url', query)
                    total_videos = len(info['entries'])

                    if status_msg:
                        playlist_embed = self.create_embed(
                            "Adding Playlist",
                            f"[🎵 {playlist_title}]({playlist_url})\nDownloading first song...",
                            color=0x3498db,
                            thumbnail_url=video_thumbnail
                        )
                        await status_msg.edit(embed=playlist_embed)

                    # Download only the first video initially
                    first_entry = info['entries'][0]
                    if not first_entry:
                        raise Exception("Failed to get first video from playlist")

                    # Download first video
                    first_video_info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(
                        first_entry['webpage_url'] if first_entry.get('webpage_url') else first_entry['url'],
                        download=True
                    ))

                    if first_video_info.get('_type') == 'playlist':
                        first_video_info = first_video_info['entries'][0]

                    # Get the file path for first video
                    first_file_path = os.path.join(self.downloads_dir, f"{first_video_info['id']}.{first_video_info.get('ext', 'opus')}")

                    # Create first song entry
                    first_song = {
                        'title': first_video_info['title'],
                        'url': first_video_info['webpage_url'] if first_video_info.get('webpage_url') else first_video_info['url'],
                        'file_path': first_file_path,
                        'thumbnail': first_video_info.get('thumbnail'),
                        'ctx': ctx,
                        'is_from_playlist': True
                    }

                    # Queue the remaining videos for background download
                    remaining_entries = info['entries'][1:]
                    asyncio.create_task(self._queue_playlist_videos(
                        entries=remaining_entries,
                        ctx=ctx,
                        is_from_playlist=True,
                        status_msg=status_msg,
                        ydl_opts=ydl_opts,
                        playlist_title=playlist_title,
                        playlist_url=playlist_url,
                        total_videos=total_videos
                    ))

                    # Return the first song to start playing immediately
                    return first_song

                else:
                    # Download the video
                    video_info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(
                        info['webpage_url'] if info.get('webpage_url') else info['url'],
                        download=True
                    ))

                    # Sometimes yt-dlp returns a playlist format even for single videos
                    if video_info.get('_type') == 'playlist':
                        video_info = video_info['entries'][0]

                    # Get the file path
                    file_path = os.path.join(self.downloads_dir, f"{video_info['id']}.{video_info.get('ext', 'opus')}")

                    # Delete the processing message after successful download
                    if status_msg:
                        try:
                            message_exists = True
                            try:
                                await status_msg.fetch()
                            except discord.NotFound:
                                message_exists = False
                            
                            if message_exists:
                                await status_msg.delete()
                        except Exception as e:
                            print(f"Note: Could not delete processing message: {str(e)}")
                            # Continue execution even if message deletion fails
                    
                    # Return the song info
                    return {
                        'title': video_info['title'],
                        'url': f"https://youtube.com/watch?v={video_info['id']}",
                        'file_path': file_path,
                        'thumbnail': video_info.get('thumbnail'),
                        'is_from_playlist': self.is_playlist_url(query)
                    }

        except Exception as e:
            print(f"Error downloading song: {str(e)}")
            if status_msg:
                error_embed = self.create_embed("Error", f"Error downloading song: {str(e)}", color=0xff0000)
                await status_msg.edit(embed=error_embed)
            raise

    async def handle_spotify_url(self, url, ctx, status_msg=None):
        """Handle Spotify URLs by extracting track info and downloading via YouTube"""
        try:
            # Check if Spotify client is available
            if not self.sp:
                raise ValueError("Spotify functionality is not available. Please check your Spotify credentials in .spotifyenv")

            # Extract Spotify URI type and ID
            spotify_match = re.match(r'https://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)', url)
            if not spotify_match:
                raise ValueError("Invalid Spotify URL")

            content_type, content_id = spotify_match.groups()

            if content_type == 'track':
                return await self.handle_spotify_track(content_id, ctx, status_msg)
            elif content_type == 'album':
                return await self.handle_spotify_album(content_id, ctx, status_msg)
            elif content_type == 'playlist':
                return await self.handle_spotify_playlist(content_id, ctx, status_msg)

        except Exception as e:
            print(f"Error handling Spotify URL: {str(e)}")
            if status_msg:
                error_embed = self.create_embed("Error", f"Failed to process Spotify content: {str(e)}", color=0xe74c3c)
                await status_msg.edit(embed=error_embed)
            return None

    async def handle_spotify_track(self, track_id, ctx, status_msg=None):
        """Handle a single Spotify track"""
        try:
            # Get track details from Spotify
            track = self.sp.track(track_id)
            if not track:
                raise ValueError("Could not find track on Spotify")

            # Create search query for YouTube
            artists = ", ".join([artist['name'] for artist in track['artists']])
            search_query = f"{track['name']} {artists}"

            # Update status message
            if status_msg:
                await status_msg.edit(embed=self.create_embed(
                    "Processing",
                    f"Searching for: {search_query}",
                    color=0x1DB954
                ))

            # Download using yt-dlp
            return await self.download_song(search_query, status_msg=status_msg, ctx=ctx)

        except Exception as e:
            print(f"Error handling Spotify track: {str(e)}")
            raise

    async def handle_spotify_album(self, album_id, ctx, status_msg=None):
        """Handle a Spotify album"""
        try:
            # Get album details from Spotify
            album = self.sp.album(album_id)
            if not album:
                raise ValueError("Could not find album on Spotify")

            # Update status message
            if status_msg:
                await status_msg.edit(embed=self.create_embed(
                    "Processing Album",
                    f"Processing album: {album['name']}\nTotal tracks: {album['total_tracks']}",
                    color=0x1DB954,
                    thumbnail_url=album['images'][0]['url'] if album['images'] else None
                ))

            # Get all tracks from the album
            tracks = []
            results = self.sp.album_tracks(album_id)
            tracks.extend(results['items'])
            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])

            # Process first track immediately
            if tracks:
                first_track = tracks[0]
                artists = ", ".join([artist['name'] for artist in first_track['artists']])
                search_query = f"{first_track['name']} {artists}"
                
                first_song = await self.download_song(search_query, status_msg=status_msg, ctx=ctx)
                if first_song:
                    first_song['is_from_playlist'] = True
                    self.queue.append(first_song)
                    if not self.is_playing:
                        await self.play_next(ctx)

            # Queue remaining tracks for background processing
            if len(tracks) > 1:
                asyncio.create_task(self._process_spotify_tracks(
                    tracks[1:],
                    ctx,
                    status_msg,
                    f"Album: {album['name']}"
                ))

            return first_song if tracks else None

        except Exception as e:
            print(f"Error handling Spotify album: {str(e)}")
            raise

    async def handle_spotify_playlist(self, playlist_id, ctx, status_msg=None):
        """Handle a Spotify playlist"""
        try:
            # Get playlist details from Spotify
            playlist = self.sp.playlist(playlist_id)
            if not playlist:
                raise ValueError("Could not find playlist on Spotify")

            # Update status message
            if status_msg:
                await status_msg.edit(embed=self.create_embed(
                    "Processing Playlist",
                    f"Processing playlist: {playlist['name']}\nTotal tracks: {playlist['tracks']['total']}",
                    color=0x1DB954,
                    thumbnail_url=playlist['images'][0]['url'] if playlist['images'] else None
                ))

            # Get all tracks from the playlist
            tracks = []
            results = playlist['tracks']
            tracks.extend(results['items'])
            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])

            # Process first track immediately
            if tracks:
                first_track = tracks[0]['track']
                artists = ", ".join([artist['name'] for artist in first_track['artists']])
                search_query = f"{first_track['name']} {artists}"
                
                first_song = await self.download_song(search_query, status_msg=status_msg, ctx=ctx)
                if first_song:
                    first_song['is_from_playlist'] = True
                    self.queue.append(first_song)
                    if not self.is_playing:
                        await self.play_next(ctx)

            # Queue remaining tracks for background processing
            if len(tracks) > 1:
                asyncio.create_task(self._process_spotify_tracks(
                    [t['track'] for t in tracks[1:]],
                    ctx,
                    status_msg,
                    f"Playlist: {playlist['name']}"
                ))

            return first_song if tracks else None

        except Exception as e:
            print(f"Error handling Spotify playlist: {str(e)}")
            raise

    async def _process_spotify_tracks(self, tracks, ctx, status_msg, source_name):
        """Process remaining Spotify tracks in the background"""
        try:
            total_tracks = len(tracks)
            processed = 0

            for track in tracks:
                if not track:  # Skip any None tracks
                    continue

                artists = ", ".join([artist['name'] for artist in track['artists']])
                search_query = f"{track['name']} {artists}"

                try:
                    song_info = await self.download_song(search_query, status_msg=None, ctx=ctx)
                    if song_info:
                        song_info['is_from_playlist'] = True
                        async with self.queue_lock:
                            self.queue.append(song_info)
                            if not self.is_playing and not self.voice_client.is_playing():
                                await self.play_next(ctx)
                except Exception as e:
                    print(f"Error processing track '{track['name']}': {str(e)}")
                    continue

                processed += 1
                if status_msg and processed % 5 == 0:  # Update status every 5 tracks
                    try:
                        await status_msg.edit(embed=self.create_embed(
                            "Processing",
                            f"Processing {source_name}\nProgress: {processed}/{total_tracks} tracks",
                            color=0x1DB954
                        ))
                    except:
                        pass  # Ignore if message edit fails

            # Final status update
            if status_msg:
                final_embed = self.create_embed(
                    "Complete",
                    f"Finished processing {source_name}\nTotal tracks added: {processed}",
                    color=0x1DB954
                )
                try:
                    await status_msg.edit(embed=final_embed)
                    await status_msg.delete(delay=5)
                except:
                    pass

        except Exception as e:
            print(f"Error in _process_spotify_tracks: {str(e)}")

    async def _handle_playlist(self, url, ctx, status_msg=None):
        """Handle a YouTube playlist by extracting video links and downloading them sequentially"""
        try:
            # First extract all video information
            ydl_opts = {
                'extract_flat': True,  # Don't download videos yet
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First extract info without downloading to check if it's a playlist
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                
                if not info or not info.get('entries'):
                    raise Exception("Could not extract playlist information")

                total_videos = len(info['entries'])

                # Update status message if provided
                if status_msg:
                    playlist_embed = self.create_embed(
                        "Processing Playlist",
                        f"Extracted {total_videos} links. Starting downloads...",
                        color=0x3498db
                    )
                    await status_msg.edit(embed=playlist_embed)

                # Join voice channel if not already in one
                if not self.voice_client or not self.voice_client.is_connected():
                    await self.join_voice_channel(ctx)

                # Download and play the first video
                if info['entries']:
                    first_entry = info['entries'][0]
                    if first_entry:
                        first_url = f"https://youtube.com/watch?v={first_entry['id']}"
                        first_song = await self.download_song(first_url, status_msg=None)
                        if first_song:
                            self.queue.append(first_song)
                            # Start playing immediately
                            if not self.is_playing:
                                await self.play_next(ctx)

                # Start background task for remaining videos
                if len(info['entries']) > 1:
                    asyncio.create_task(self._process_playlist_downloads(info['entries'][1:], ctx, status_msg))

                return True

        except Exception as e:
            print(f"Error processing playlist: {str(e)}")
            if status_msg:
                error_embed = self.create_embed(
                    "Error",
                    f"Failed to process playlist: {str(e)}",
                    color=0xe74c3c
                )
                await status_msg.edit(embed=error_embed)
            return False

    async def _process_playlist_downloads(self, entries, ctx, status_msg=None):
        """Process remaining playlist videos in the background"""
        try:
            for entry in entries:
                if entry:
                    video_url = f"https://youtube.com/watch?v={entry['id']}"
                    song_info = await self.download_song(video_url, status_msg=None)
                    if song_info:
                        async with self.queue_lock:
                            self.queue.append(song_info)
                            # Start playing if not already playing
                            if not self.is_playing and not self.voice_client.is_playing():
                                await self.play_next(ctx)

            # Final status update
            if status_msg:
                final_embed = self.create_embed(
                    "Playlist Complete",
                    f"All songs have been downloaded and queued",
                    color=0x00ff00
                )
                try:
                    await status_msg.edit(embed=final_embed)
                    await status_msg.delete(delay=5)  # Remove processing message after all songs are processed
                except:
                    pass

        except Exception as e:
            print(f"Error in playlist download processing: {str(e)}")

    async def _queue_playlist_videos(self, entries, ctx, is_from_playlist, status_msg, ydl_opts, playlist_title, playlist_url, total_videos):
        """Process remaining playlist videos in the background"""
        try:
            for entry in entries:
                if entry:
                    video_url = f"https://youtube.com/watch?v={entry['id']}"
                    song_info = await self.download_song(video_url, status_msg=None)
                    if song_info:
                        async with self.queue_lock:
                            self.queue.append(song_info)
                            # Start playing if not already playing
                            if not self.is_playing and not self.voice_client.is_playing():
                                await self.play_next(ctx)

            # Final status update
            if status_msg:
                final_embed = self.create_embed(
                    "Playlist Complete",
                    f"All songs have been downloaded and queued",
                    color=0x00ff00
                )
                try:
                    await status_msg.edit(embed=final_embed)
                    await status_msg.delete(delay=5)  # Remove processing message after all songs are processed
                except:
                    pass

        except Exception as e:
            print(f"Error in playlist download processing: {str(e)}")

    async def play(self, ctx, *, query=None):
        """Play a song in the voice channel"""
        try:
            # Check if query is provided
            if not query:
                usage_embed = self.create_embed(
                    "Usage",
                    "Usage: !play YouTube Link/Youtube Search/Spotify Link",
                    color=0xe74c3c
                )
                await ctx.send(embed=usage_embed)
                return

            # Check if the user is in a voice channel
            if not ctx.author.voice:
                embed = self.create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c)
                await ctx.send(embed=embed)
                return

            # Create voice client if not exists
            if not ctx.guild.voice_client:
                await ctx.author.voice.channel.connect()
            elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
                await ctx.guild.voice_client.move_to(ctx.author.voice.channel)

            music_bot.voice_client = ctx.guild.voice_client

            # Create a unique processing message for this request
            processing_embed = self.create_embed(
                "Processing",
                f"Processing your request...",
                color=0x3498db
            )
            status_msg = await ctx.send(embed=processing_embed)

            # Check if it's a Spotify URL
            if 'open.spotify.com' in query:
                result = await self.handle_spotify_url(query, ctx, status_msg)
                if not result:
                    return
            else:
                # Handle as regular YouTube query
                async with self.queue_lock:
                    result = await self.download_song(query, status_msg=status_msg, ctx=ctx)
                    if not result:
                        return

                    # Add the song to the queue
                    self.queue.append({
                        'title': result['title'],
                        'url': result['url'],
                        'file_path': result['file_path'],
                        'thumbnail': result.get('thumbnail'),
                        'ctx': ctx,
                        'is_stream': result.get('is_stream', False),
                        'is_from_playlist': result.get('is_from_playlist', False)
                    })

                    # If not currently playing, start playing
                    if not self.is_playing and not self.waiting_for_song:
                        await self.process_queue()
                    else:
                        # Only send "Added to queue" message if it's not from a playlist
                        if not result.get('is_from_playlist'):
                            queue_pos = len(self.queue)
                            queue_embed = self.create_embed(
                                "Added to Queue",
                                f"[🎵 {result['title']}]({result['url']})\nPosition in queue: {queue_pos}",
                                color=0x3498db,
                                thumbnail_url=result.get('thumbnail')
                            )
                            queue_msg = await ctx.send(embed=queue_embed)
                            # Store the queue message
                            self.queued_messages[result['url']] = queue_msg

        except Exception as e:
            error_msg = f"Error playing song: {str(e)}"
            print(error_msg)
            error_embed = self.create_embed("Error", error_msg, color=0xff0000)
            await ctx.send(embed=error_embed)

    async def after_playing_coro(self, error, ctx):
        """Coroutine called after a song finishes playing"""
        if error:
            print(f"Error in playback: {error}")
        
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
            # Update the now playing message to show playback has finished
            if self.now_playing_message:
                try:
                    finished_embed = self.create_embed(
                        "Finished Playing",
                        f"[{self.current_song['title']}]({self.current_song['url']})",
                        color=0x808080,  # Green color to indicate completion
                        thumbnail_url=self.current_song.get('thumbnail')
                    )
                    await self.now_playing_message.edit(embed=finished_embed)
                except Exception as e:
                    print(f"Error updating finished message: {str(e)}")
            
            # Clear status first
            self.is_playing = False
            self.current_song = None
            await self.update_activity()  # This will now clear the activity
            
            # Then handle disconnection
            # if self.download_queue.empty():  # Only disconnect if nothing left to download
            #     if self.voice_client and self.voice_client.is_connected():
            #         await self.voice_client.disconnect()

    async def queue(self, ctx):
        """Display the current queue"""
        if not self.queue and not self.current_song:
            embed = self.create_embed("Queue Empty", "No songs in queue", color=0xe74c3c)
            await ctx.send(embed=embed)
            return
            
        # Create queue embed
        queue_text = ""
        total_songs = len(self.queue)
        
        # Add currently playing song
        if self.current_song:
            status = "🔁 Now playing" if self.loop_mode else "▶️ Now playing"
            queue_text += f"{status}: [{self.current_song['title']}]({self.current_song['url']})\n\n"
        
        # Add queued songs
        if self.queue:
            queue_text += "**Up Next:**\n"
            for i, song in enumerate(self.queue[:10], 1):
                queue_text += f"`{i}.` [{song['title']}]({song['url']})\n"
            
            if len(self.queue) > 10:
                queue_text += f"\n*...and {len(self.queue) - 10} more songs*"
        
        # Add download queue info
        if not self.download_queue.empty():
            queue_text += f"\n\n*{self.download_queue.qsize()} songs being processed...*"
        
        embed = self.create_embed(
            f"Queue - {total_songs} songs",
            queue_text,
            color=0x3498db
        )
        await ctx.send(embed=embed)
    
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
            self.current_command_author = ctx.author_id
            return self.current_command_msg

    async def update_activity(self):
        """Update the bot's activity status"""
        try:
            if self.bot:
                if self.current_song and self.is_playing:
                    activity = discord.Activity(
                        type=discord.ActivityType.playing,
                        name=f"🎵 {self.current_song['title']}"
                    )
                else:
                    # Set default listening status
                    activity = discord.Activity(
                        type=discord.ActivityType.playing,
                        name="nothing! use !play "
                    )
                await self.bot.change_presence(activity=activity)
        except Exception as e:
            print(f"Error updating activity: {str(e)}")

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
    
    # Clear downloads folder on startup
    clear_downloads_folder()
    
    # Set initial status immediately
    await bot.change_presence(activity=discord.Game(name="nothing! use !play "))
    
    print(f"Logged in as {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    print("------")
    
    # Initialize the music bot
    if not music_bot:
        music_bot = MusicBot()
        await music_bot.setup(bot)

@bot.command(name='play')
async def play(ctx, *, query=None):
    """Play a song in the voice channel"""
    try:
        # Check if query is provided
        if not query:
            usage_embed = music_bot.create_embed(
                "Usage",
                "Usage: !play YouTube Link/Youtube Search/Spotify Link",
                color=0xe74c3c
            )
            await ctx.send(embed=usage_embed)
            return

        # Check if the user is in a voice channel
        if not ctx.author.voice:
            embed = music_bot.create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c)
            await ctx.send(embed=embed)
            return

        # Create voice client if not exists
        if not ctx.guild.voice_client:
            await ctx.author.voice.channel.connect()
        elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
            await ctx.guild.voice_client.move_to(ctx.author.voice.channel)

        music_bot.voice_client = ctx.guild.voice_client

        # Create a unique processing message for this request
        processing_embed = music_bot.create_embed(
            "Processing",
            f"Processing your request...",
            color=0x3498db
        )
        status_msg = await ctx.send(embed=processing_embed)

        # Check if it's a Spotify URL
        if 'open.spotify.com' in query:
            result = await music_bot.handle_spotify_url(query, ctx, status_msg)
            if not result:
                return
        else:
            # Handle as regular YouTube query
            async with music_bot.queue_lock:
                result = await music_bot.download_song(query, status_msg=status_msg, ctx=ctx)
                if not result:
                    return

                # Add the song to the queue
                music_bot.queue.append({
                    'title': result['title'],
                    'url': result['url'],
                    'file_path': result['file_path'],
                    'thumbnail': result.get('thumbnail'),
                    'ctx': ctx,
                    'is_stream': result.get('is_stream', False),
                    'is_from_playlist': result.get('is_from_playlist', False)
                })

                # If not currently playing, start playing
                if not music_bot.is_playing and not music_bot.waiting_for_song:
                    await music_bot.process_queue()
                else:
                    # Only send "Added to queue" message if it's not from a playlist
                    if not result.get('is_from_playlist'):
                        queue_pos = len(music_bot.queue)
                        queue_embed = music_bot.create_embed(
                            "Added to Queue",
                            f"[🎵 {result['title']}]({result['url']})\nPosition in queue: {queue_pos}",
                            color=0x3498db,
                            thumbnail_url=result.get('thumbnail')
                        )
                        queue_msg = await ctx.send(embed=queue_embed)
                        # Store the queue message
                        music_bot.queued_messages[result['url']] = queue_msg

    except Exception as e:
        error_msg = f"Error playing song: {str(e)}"
        print(error_msg)
        error_embed = music_bot.create_embed("Error", error_msg, color=0xff0000)
        await ctx.send(embed=error_embed)

@bot.command(name='pause')
async def pause(ctx):
    """Pause the currently playing song"""
    try:
        # Removed music_bot.update_activity() as it does not exist
        if music_bot.voice_client and music_bot.voice_client.is_playing():
            music_bot.voice_client.pause()
            music_bot.last_activity = time.time()  # Update activity on pause
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
        print(f"Error in pause command: {str(e)}")  # Log the error to the console
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
        # Removed music_bot.update_activity() as it does not exist
        if music_bot.voice_client and music_bot.voice_client.is_paused():
            music_bot.voice_client.resume()
            music_bot.last_activity = time.time()  # Update activity on resume
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
        print(f"Error in resume command: {str(e)}")  # Log the error to the console
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
        await ctx.send(embed=music_bot.create_embed("Stopped", "Music stopped and queue cleared", color=0xe74c3c))

    except Exception as e:
        await ctx.send(embed=music_bot.create_embed("Error", f"An error occurred while stopping: {str(e)}", color=0xe74c3c))

@bot.command(name='skip')
async def skip(ctx):
    """Skip the current song"""
    if music_bot.voice_client and (music_bot.voice_client.is_playing() or music_bot.voice_client.is_paused()):
        music_bot.voice_client.stop()
        music_bot.last_activity = time.time()  # Update activity on skip
        await ctx.send(embed=music_bot.create_embed("Skipped", "Skipped the current song", color=0x3498db))
    else:
        await ctx.send(embed=music_bot.create_embed("Error", "Nothing is playing to skip", color=0xe74c3c))

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
    try:
        # Upload the log.txt file to the chat
        await ctx.send(file=discord.File('log.txt'))
    except Exception as e:
        await ctx.send(f"Error uploading log file: {str(e)}")

@bot.command(name='leave')
async def leave(ctx):
    """Leave the voice channel"""
    if music_bot and music_bot.voice_client and music_bot.voice_client.is_connected():
        await music_bot.leave_voice_channel()
        await ctx.send(embed=music_bot.create_embed("Left Channel", "Disconnected from voice channel", color=0x3498db))
    else:
        await ctx.send(embed=music_bot.create_embed("Error", "I'm not in a voice channel", color=0xe74c3c))

@bot.command(name='loop', aliases=['repeat'])
async def loop(ctx):
    """Toggle loop mode for the current song"""
    if not music_bot.current_song:
        await ctx.send(embed=music_bot.create_embed("Error", "No song is currently playing!", color=0xe74c3c))
        return

    # Toggle loop mode
    music_bot.loop_mode = not music_bot.loop_mode
    
    # Send status message
    status = "enabled" if music_bot.loop_mode else "disabled"
    color = 0x2ecc71 if music_bot.loop_mode else 0xe74c3c
    
    await ctx.send(embed=music_bot.create_embed(f"Loop Mode {status.title()}", f"[🎵 {music_bot.current_song['title']}]({music_bot.current_song['url']}) will {'now' if music_bot.loop_mode else 'no longer'} be looped", color=color))

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

@bot.command(name='logclear')
async def logclear(ctx):
    """Clear the log file - Owner only command"""
    if ctx.author.id != OWNER_ID:  # Owner ID check
        await ctx.send(embed=discord.Embed(title="Error", description="This command is only available to the bot owner.", color=0xe74c3c))
        return

    try:
        # Clear the log file
        with open('log.txt', 'w', encoding='utf-8') as f:
            f.write('---')  # Write empty string to clear the file
        
        # Send success message
        await ctx.send(embed=discord.Embed(title="Success", description="Log file has been cleared.", color=0x2ecc71))
        print("Log file cleared by owner")
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"Failed to clear log file: {str(e)}", color=0xe74c3c))

@bot.command(name='max')
async def max(ctx):
    """Simulate !play with RadioMax URL"""
    try:
        await play(ctx, query='https://azuracast.novi-net.net/radio/8010/radiomax.aac')
    except Exception as e:
        await ctx.send(embed=music_bot.create_embed("Error", f"An error occurred while executing !max: {str(e)}", color=0xe74c3c))

@bot.command(name='nowplaying', aliases=['np'])
async def nowplaying(ctx):
    """Show the currently playing song"""
    if not music_bot:
        return

    if not music_bot.current_song:
        await ctx.send("No song is currently playing.")
        return

    # Create embed with current song info
    embed = music_bot.create_embed(
        "Now Playing 🎵",
        f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})",
        color=0x3498db,
        thumbnail_url=music_bot.current_song.get('thumbnail')
    )

    await ctx.send(embed=embed)

# Remove default help command before registering custom one
bot.remove_command('help')

@bot.command(name='help')
async def help_command(ctx):
    """Send an embedded message with all commands and explanations"""
    help_embed = discord.Embed(title="Help - Commands", description="List of available commands:", color=0x3498db)
    help_embed.add_field(name="!play [URL/search term]", value="Play a song from YouTube or Spotify.", inline=False)
    help_embed.add_field(name="!pause", value="Pause the current song.", inline=False)
    help_embed.add_field(name="!resume", value="Resume playback.", inline=False)
    help_embed.add_field(name="!skip", value="Skip the current song.", inline=False)
    help_embed.add_field(name="!queue", value="Show the current song queue.", inline=False)
    help_embed.add_field(name="!leave", value="Leave the voice channel.", inline=False)
    help_embed.add_field(name="!loop", value="Toggle loop mode for the current song.", inline=False)
    help_embed.add_field(name="!stop", value="Stop playback, clear the queue, and leave the voice channel.", inline=False)
    help_embed.add_field(name="!log", value="Log the current context.", inline=False)
    help_embed.add_field(name="!restart", value="Restart the bot (Owner only).", inline=False)
    help_embed.add_field(name="!logclear", value="Clear the log file (Owner only command).", inline=False)
    help_embed.add_field(name="!nowplaying", value="Show the currently playing song.", inline=False)
    await ctx.send(embed=help_embed)

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN'))
