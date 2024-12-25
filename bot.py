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
from scripts.updatescheduler import check_updates, update_checker
from scripts.voice import join_voice_channel, leave_voice_channel
from scripts.inactivity import start_inactivity_checker, check_inactivity
from scripts.messages import update_or_send_message
from spotipy.oauth2 import SpotifyClientCredentials
from scripts.ytdlp import get_ytdlp_path, ytdlp_version
from scripts.ffmpeg import check_ffmpeg_in_path, install_ffmpeg_windows, install_ffmpeg_macos, install_ffmpeg_linux, get_ffmpeg_path
from scripts.cleardownloads import clear_downloads_folder
from scripts.restart import restart_bot
from scripts.load_commands import load_commands
from scripts.load_scripts import load_scripts
from scripts.activity import update_activity
from scripts.spotify import get_spotify_album_details, get_spotify_track_details, get_spotify_playlist_details

if not os.path.exists('config.json'):
    default_config = {
        "OWNER_ID": "YOUR_DISCORD_USER_ID",
        "PREFIX": "!"}
    with open('config.json', 'w') as f:
        json.dump(default_config, f, indent=4)

with open('config.json', 'r') as f:
    config = json.load(f)
    OWNER_ID = config['OWNER_ID']
    PREFIX = config['PREFIX']

YTDLP_PATH = get_ytdlp_path()
FFMPEG_PATH = get_ffmpeg_path()

file_handler = logging.FileHandler('log.txt', encoding='utf-8')
console_handler = logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[file_handler, console_handler]
)

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('yt-dlp').setLevel(logging.INFO)
logging.getLogger('discord.player').setLevel(logging.INFO)
logging.getLogger('discord.client').setLevel(logging.INFO)
logging.getLogger('discord.voice_client').setLevel(logging.INFO)
logging.getLogger('discord.gateway').setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.INFO)
logging.getLogger('discord.state').setLevel(logging.INFO)
logging.getLogger('discord.interactions').setLevel(logging.INFO)
logging.getLogger('discord.webhook').setLevel(logging.INFO)
logging.getLogger('discord.ext.commands').setLevel(logging.INFO)
logging.getLogger('discord.ext.tasks').setLevel(logging.INFO)
logging.getLogger('discord.ext.voice_client').setLevel(logging.INFO)
logging.getLogger('discord.ext.commands.bot').setLevel(logging.INFO)
logging.getLogger('discord.ext.commands.core').setLevel(logging.INFO)
logging.getLogger('discord.ext.commands.errors').setLevel(logging.INFO)
logging.getLogger('discord.ext.commands.cog').setLevel(logging.INFO)
logging.getLogger('discord.ext.tasks.loop').setLevel(logging.INFO)
logging.getLogger('discord.ext').setLevel(logging.INFO)
logging.getLogger('discord.utils').setLevel(logging.INFO)
logging.getLogger('discord.intents').setLevel(logging.INFO)

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

load_dotenv(dotenv_path=".spotifyenv")

log_buffer = deque(maxlen=100)

original_print = print
def custom_print(*args, **kwargs):
    output = " ".join(map(str, args))
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {output}"
    log_buffer.append(log_entry)
    original_print(*args, **kwargs)

print = custom_print

DOWNLOADS_DIR = os.path.join(os.getcwd(), 'downloads')
OWNER_ID = config['OWNER_ID']

if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    owner_id=int(config['OWNER_ID'])
)

@bot.event
async def on_command_error(ctx, error):
    print(f"Error in command {ctx.command}: {str(error)}")
    await ctx.send(
        embed=music_bot.create_embed(
            "Error",
            f"Error: {str(error)}",
            color=0xe74c3c
        )
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Error: {str(error)}")

@bot.event
async def on_voice_state_update(member, before, after):
    global music_bot
    if not music_bot or not music_bot.voice_client:
        return

    bot_voice_channel = music_bot.voice_client.channel
    if not bot_voice_channel:
        return

    members_in_channel = sum(1 for m in bot_voice_channel.members if not m.bot)

    if members_in_channel == 0:
        if music_bot and music_bot.voice_client and music_bot.voice_client.is_connected():
            if music_bot.voice_client.is_playing() or music_bot.queue:
                music_bot.voice_client.stop()
                music_bot.queue.clear()
                music_bot.current_song = None
                music_bot.is_playing = False
            await music_bot.voice_client.disconnect()
        print(f"No users in voice channel {bot_voice_channel.name}, disconnecting bot")

YTDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a][abr<=96]/bestaudio[abr<=96]/bestaudio/best/bestaudio*',
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
    'ffmpeg_location': FFMPEG_PATH,
    'yt_dlp_filename': get_ytdlp_path()
}

FFMPEG_OPTIONS = {
    'executable': FFMPEG_PATH,
    'options': '-loglevel warning -vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}

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
                speed_mb = speed / 1024 / 1024 if speed else 0
                
                status = f"Downloading: {self.title}\n"
                status += f"\n{progress_bar} {percentage:.1f}%\n"
                status += f"Speed: {speed_mb:.1f} MB/s"
                
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
        self.queue = []
        self.current_song = None
        self.is_playing = False
        self.voice_client = None
        self.loop_mode = False
        self.waiting_for_song = False
        self.queue_lock = asyncio.Lock()
        self.download_queue = asyncio.Queue()
        self.currently_downloading = False
        self.command_queue = asyncio.Queue()
        self.command_processor_task = None
        self.download_lock = asyncio.Lock()
        self.bot_loop = None
        self.queued_messages = {}
        self.current_command_msg = None
        self.current_command_author = None
        self.status_messages = {}
        self.now_playing_message = None
        self.downloads_dir = os.path.join(os.getcwd(), 'downloads')
        self.cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
        
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)

        self.last_activity = time.time()
        self.inactivity_timeout = 60
        self._inactivity_task = None
        self.last_update = 0
        self._last_progress = -1
        self.last_known_ctx = None
        self.bot = None

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
        await start_inactivity_checker(self)
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
                command_info = await self.command_queue.get()
                self.last_activity = time.time()
                ctx, query = command_info
                print(f"Processing command: !play {query}")

                try:
                    await self._handle_play_command(ctx, query)
                except Exception as e:
                    print(f"Error processing command: {e}")
                    error_embed = self.create_embed("Error", f"Failed to process command: {str(e)}", color=0xe74c3c)
                    await self.update_or_send_message(ctx, error_embed)
                finally:
                    self.command_queue.task_done()
            except Exception as e:
                print(f"Error in command processor: {str(e)}")
                await asyncio.sleep(1)

    async def _handle_play_command(self, ctx, query):
        """Internal method to handle a single play command"""
        if not ctx.voice_client and not await self.join_voice_channel(ctx):
            raise Exception("Could not join voice channel")

        self.last_activity = time.time()
        processing_embed = self.create_embed(
            "Processing",
            f"Processing request: {query}",
            color=0x3498db
        )
        status_msg = await self.update_or_send_message(ctx, processing_embed)

        download_info = {
            'query': query,
            'ctx': ctx,
            'status_msg': status_msg
        }

        await self.download_queue.put(download_info)
        print(f"Added to download queue: {query}")

    async def process_download_queue(self):
        """Process the download queue sequentially"""
        while True:
            try:
                download_info = await self.download_queue.get()
                
                query = download_info['query']
                ctx = download_info['ctx']
                status_msg = download_info['status_msg']

                try:
                    async with self.download_lock:
                        self.currently_downloading = True
                        print(f"Starting download: {query}")
                        
                        result = await self.download_song(query, status_msg=status_msg, ctx=ctx)
                        
                        if not result:
                            if not status_msg:
                                error_embed = self.create_embed("Error", "Failed to download song", color=0xe74c3c)
                                await self.update_or_send_message(ctx, error_embed)
                            continue

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
                        else:
                            if status_msg:
                                playlist_embed = self.create_embed(
                                    "Adding Playlist",
                                    f"Adding {len(result['entries'])} songs to queue...",
                                    color=0x3498db
                                )
                                await status_msg.edit(embed=playlist_embed)

                        if self.voice_client and self.voice_client.is_playing():
                            self.queue.append(result)
                            if not result.get('is_from_playlist'):
                                queue_embed = self.create_embed(
                                    "Added to Queue", 
                                    f"[🎵 {result['title']}]({result['url']})",
                                    color=0x3498db,
                                    thumbnail_url=result.get('thumbnail')
                                )
                                queue_msg = await ctx.send(embed=queue_embed)
                                self.queued_messages[result['url']] = queue_msg
                        else:
                            self.queue.append(result)
                            await self.play_next(ctx)

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
                await asyncio.sleep(1)

    def clear_queue(self):
        """Clear both download and playback queues"""
        try:
            self.queue.clear()
            
            items_removed = 0
            while not self.download_queue.empty():
                try:
                    self.download_queue.get_nowait()
                    items_removed += 1
                except asyncio.QueueEmpty:
                    break
            
            for _ in range(items_removed):
                self.download_queue.task_done()
                
        except Exception as e:
            print(f"Error clearing queue: {e}")

    async def stop(self, ctx):
        """Stop playing and clear the queue"""
        try:
            if self.voice_client:
                if self.voice_client.is_playing():
                    self.voice_client.stop()
                    await asyncio.sleep(0.5)
                await self.voice_client.disconnect()

            self.clear_queue()
            self.current_song = None
            await self.bot.change_presence(activity=discord.Game(name="nothing! use !play "))
            
            await ctx.send(embed=self.create_embed("Stopped", "Music stopped and queue cleared", color=0xe74c3c))

        except Exception as e:
            print(f"Error in stop command: {str(e)}")
            await ctx.send(embed=self.create_embed("Error", "Failed to stop playback", color=0xe74c3c))

    async def play_next(self, ctx):
        """Play the next song in the queue"""
        if len(self.queue) > 0:
            try:
                previous_song = self.current_song
                self.current_song = self.queue.pop(0)
                self.last_activity = time.time()
                print(f"Playing next song: {self.current_song['title']}")
                
                if not self.current_song.get('is_stream'):
                    if not os.path.exists(self.current_song['file_path']):
                        print(f"Error: File not found: {self.current_song['file_path']}")
                        if len(self.queue) > 0:
                            await self.play_next(ctx)
                        return

                if not self.voice_client or not self.voice_client.is_connected():
                    print("Voice client not connected, attempting to reconnect...")
                    connected = await self.join_voice_channel(ctx)
                    if not connected:
                        print("Failed to reconnect to voice channel")
                        self.voice_client = None
                        
                        try:
                            await ctx.send("⚠️ Internal error detected!. Automatically restarting bot...")
                            restart_cog = self.bot.get_cog('Restart')
                            if restart_cog:
                                await restart_cog.restart_cmd(ctx)
                        except Exception as e:
                            print(f"Error during automatic restart in play_next: {str(e)}")
                        return
                else:
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

                    now_playing_embed = self.create_embed(
                        "Now Playing",
                        f"[🎵 {self.current_song['title']}]({self.current_song['url']})",
                        color=0x00ff00,
                        thumbnail_url=self.current_song.get('thumbnail')
                    )
                    self.now_playing_message = await ctx.send(embed=now_playing_embed)
                    
                    await self.bot.change_presence(activity=discord.Game(name=f"{self.current_song['title']}"))
                    
                    self.current_command_msg = None
                    self.current_command_author = None

                    try:
                        if self.voice_client and self.voice_client.is_connected():
                            ffmpeg_options = {
                                'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                            }
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
            await self.bot.change_presence(activity=discord.Game(name="nothing! use !play "))
            if self.download_queue.empty():
                if self.voice_client and self.voice_client.is_connected():
                    await self.voice_client.disconnect()

    async def process_queue(self):
        """Process the song queue"""
        if self.waiting_for_song or not self.queue:
            return

        self.waiting_for_song = True

        try:
            song = self.queue.pop(0)
            
            ctx = song.get('ctx')
            if not ctx:
                print("Warning: Missing context in song, using last known context")
                if hasattr(self, 'last_known_ctx'):
                    ctx = self.last_known_ctx
                else:
                    print("Error: No context available for playback")
                    self.waiting_for_song = False
                    if self.queue:
                        await self.process_queue()
                    return

            self.last_known_ctx = ctx

            if not self.voice_client or not self.voice_client.is_connected():
                print("Not connected to voice during process_queue")
                try:
                    if ctx:
                        await ctx.send("⚠️ Voice connection lost. Automatically restarting bot...")
                    
                    restart_cog = self.bot.get_cog('Restart')
                    if restart_cog:
                        await restart_cog.restart_cmd(ctx)
                except Exception as e:
                    print(f"Error during automatic restart in process_queue: {str(e)}")
                return

            if song['url'] in self.queued_messages:
                try:
                    await self.queued_messages[song['url']].delete()
                except Exception as e:
                    print(f"Error deleting queue message: {str(e)}")
                finally:
                    del self.queued_messages[song['url']]

            self.current_song = song
            self.is_playing = True
            
            now_playing_embed = self.create_embed(
                "Now Playing",
                f"[🎵 {song['title']}]({song['url']})",
                color=0x00ff00,
                thumbnail_url=song.get('thumbnail')
            )
            self.now_playing_message = await ctx.send(embed=now_playing_embed)
            
            await self.bot.change_presence(activity=discord.Game(name=f"{song['title']}"))
            
            if song.get('is_stream'):
                audio_source = discord.FFmpegPCMAudio(
                    song['file_path'],
                    **FFMPEG_OPTIONS
                )
            else:
                audio_source = discord.FFmpegPCMAudio(
                    song['file_path'],
                    **FFMPEG_OPTIONS
                )

            audio_source = discord.PCMVolumeTransformer(audio_source, volume=0.75)

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
                
                async def update_now_playing():
                    try:
                        if current_message:
                            finished_embed = self.create_embed(
                                "Finished Playing",
                                f"[{current_song_info['title']}]({current_song_info['url']})",
                                color=0x808080,
                                thumbnail_url=current_song_info.get('thumbnail')
                            )
                            await current_message.edit(embed=finished_embed)
                        
                        self.is_playing = False
                        self.waiting_for_song = False
                        self.current_song = None
                        self.now_playing_message = None
                        await self.bot.change_presence(activity=discord.Game(name="nothing! use !play "))
                        await self.process_queue()
                    except Exception as e:
                        print(f"Error updating finished message: {str(e)}")
                
                asyncio.run_coroutine_threadsafe(update_now_playing(), self.bot_loop)

            self.voice_client.play(audio_source, after=after_playing)

        except Exception as e:
            print(f"Error in process_queue: {str(e)}")
            if ctx:
                error_embed = self.create_embed("Error", f"Error playing song: {str(e)}", color=0xff0000)
                await ctx.send(embed=error_embed)

        finally:
            self.waiting_for_song = False
            if not self.is_playing:
                await self.process_queue()

    async def update_or_send_message(self, ctx, embed, view=None, force_new=False):
        """Update existing message or send a new one if none exists or if it's a new command"""
        try:
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
            self.current_command_msg = await ctx.send(embed=embed, view=view)
            self.current_command_author = ctx.author_id
            return self.current_command_msg

    def is_radio_stream(self, url):
        """Check if the URL is a radio stream"""
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
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    downloaded = d.get('downloaded_bytes', 0)
                    percentage = int((downloaded / total) * 100)
                    
                    if percentage % 10 == 0 and percentage != self._last_progress:
                        self._last_progress = percentage
                        progress_bar = self.create_progress_bar(percentage)
                        
                        total_size = self.format_size(total)
                        
                        try:
                            await status_msg.fetch()
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
        return query.startswith(('http://', 'https://', 'www.'))

    async def download_song(self, query, status_msg=None, ctx=None):
        """Download a song from YouTube, Spotify, or handle radio stream"""
        try:
            self._last_progress = -1

            if self.is_playlist_url(query):
                ctx = ctx or status_msg.channel if status_msg else None
                await self._handle_playlist(query, ctx, status_msg)
                return None
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

            if self.is_radio_stream(query):
                print("Radio stream detected")
                try:
                    stream_name = query.split('/')[-1].split('.')[0]
                    result = {
                        'title': stream_name,
                        'url': query,
                        'file_path': query,  
                        'is_stream': True,
                        'thumbnail': None
                    }
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

            if not os.path.exists(self.downloads_dir):
                os.makedirs(self.downloads_dir)

            if not self.is_url(query):
                query = f"ytsearch:{query}"

            ydl_opts = {
                **YTDL_OPTIONS,
                'outtmpl': os.path.join(self.downloads_dir, '%(id)s.%(ext)s'),
                'cookiefile': self.cookie_file if os.path.exists(self.cookie_file) else None,
                'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(
                    self.progress_hook(d, status_msg), 
                    self.bot_loop
                )] if status_msg else [],
                'default_search': 'ytsearch'
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                
                if info.get('_type') == 'playlist' and not self.is_playlist_url(query):
                    if not info.get('entries'):
                        raise Exception("No search results found")
                    info = info['entries'][0]
                    
                    video_info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(
                        info['webpage_url'],
                        download=True
                    ))
                    
                    if video_info.get('_type') == 'playlist':
                        video_info = video_info['entries'][0]
                    
                    file_path = os.path.join(self.downloads_dir, f"{video_info['id']}.{video_info.get('ext', 'opus')}")
                    
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
                    
                    return {
                        'title': video_info['title'],
                        'url': video_info['webpage_url'] if video_info.get('webpage_url') else video_info['url'],
                        'file_path': file_path,
                        'thumbnail': video_info.get('thumbnail'),
                        'is_from_playlist': False,
                        'ctx': status_msg.channel if status_msg else None
                    }
                elif info.get('_type') == 'playlist' and self.is_playlist_url(query):
                    if not info.get('entries'):
                        raise Exception("Playlist is empty")

                    ctx = ctx or status_msg.channel if status_msg else None

                    first_video = info['entries'][0]
                    video_thumbnail = first_video.get('thumbnail')

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

                    if info['entries']:
                        first_entry = info['entries'][0]
                        if not first_entry:
                            raise Exception("Failed to get first video from playlist")

                        first_video_info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(
                            first_entry['webpage_url'] if first_entry.get('webpage_url') else first_entry['url'],
                            download=True
                        ))

                        if first_video_info.get('_type') == 'playlist':
                            first_video_info = first_video_info['entries'][0]

                        first_file_path = os.path.join(self.downloads_dir, f"{first_video_info['id']}.{first_video_info.get('ext', 'opus')}")

                        first_song = {
                            'title': first_video_info['title'],
                            'url': first_video_info['webpage_url'] if first_video_info.get('webpage_url') else first_video_info['url'],
                            'file_path': first_file_path,
                            'thumbnail': first_video_info.get('thumbnail'),
                            'ctx': ctx,
                            'is_from_playlist': True
                        }

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

                        return first_song

                else:
                    video_info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(
                        info['webpage_url'] if info.get('webpage_url') else info['url'],
                        download=True
                    ))

                    if video_info.get('_type') == 'playlist':
                        video_info = video_info['entries'][0]

                    file_path = os.path.join(self.downloads_dir, f"{video_info['id']}.{video_info.get('ext', 'opus')}")

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
            if not self.sp:
                raise ValueError("Spotify functionality is not available. Please check your Spotify credentials in .spotifyenv")

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
            track = self.sp.track(track_id)
            if not track:
                raise ValueError("Could not find track on Spotify")

            artists = ", ".join([artist['name'] for artist in track['artists']])
            search_query = f"{track['name']} {artists}"

            if status_msg:
                await status_msg.edit(embed=self.create_embed(
                    "Processing",
                    f"Searching for: {search_query}",
                    color=0x1DB954
                ))

            return await self.download_song(search_query, status_msg=status_msg, ctx=ctx)

        except Exception as e:
            print(f"Error handling Spotify track: {str(e)}")
            raise

    async def handle_spotify_album(self, album_id, ctx, status_msg=None):
        """Handle a Spotify album"""
        try:
            album = self.sp.album(album_id)
            if not album:
                raise ValueError("Could not find album on Spotify")

            if status_msg:
                await status_msg.edit(embed=self.create_embed(
                    "Processing Album",
                    f"Processing album: {album['name']}\nTotal tracks: {album['total_tracks']}",
                    color=0x1DB954,
                    thumbnail_url=album['images'][0]['url'] if album['images'] else None
                ))
            tracks = []
            results = self.sp.album_tracks(album_id)
            tracks.extend(results['items'])
            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])
            if tracks:
                first_track = tracks[0]
                artists = ", ".join([artist['name'] for artist in first_track['artists']])
                search_query = f"{first_track['name']} {artists}"
                first_song = await self.download_song(search_query, status_msg=status_msg, ctx=ctx)
                if first_song:
                    first_song['is_from_playlist'] = True
                    self.queue.append(first_song)
                    if not self.is_playing and not self.voice_client.is_playing():
                        await self.play_next(ctx)

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
            playlist = self.sp.playlist(playlist_id)
            if not playlist:
                raise ValueError("Could not find playlist on Spotify")

            if status_msg:
                await status_msg.edit(embed=self.create_embed(
                    "Processing Playlist",
                    f"Processing playlist: {playlist['name']}\nTotal tracks: {playlist['tracks']['total']}",
                    color=0x1DB954,
                    thumbnail_url=playlist['images'][0]['url'] if playlist['images'] else None
                ))

            tracks = []
            results = playlist['tracks']
            tracks.extend(results['items'])
            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])

            if tracks:
                first_track = tracks[0]['track']
                artists = ", ".join([artist['name'] for artist in first_track['artists']])
                search_query = f"{first_track['name']} {artists}"
                
                first_song = await self.download_song(search_query, status_msg=status_msg, ctx=ctx)
                if first_song:
                    first_song['is_from_playlist'] = True
                    self.queue.append(first_song)
                    if not self.is_playing and not self.voice_client.is_playing():
                        await self.play_next(ctx)

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
                if not track:
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
                if status_msg and processed % 5 == 0:
                    try:
                        await status_msg.edit(embed=self.create_embed(
                            "Processing",
                            f"Processing {source_name}\nProgress: {processed}/{total_tracks} tracks",
                            color=0x1DB954
                        ))
                    except:
                        pass

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
            ydl_opts = {
                'extract_flat': True,
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                
                if not info or not info.get('entries'):
                    raise Exception("Could not extract playlist information")

                total_videos = len(info['entries'])

                if status_msg:
                    playlist_embed = self.create_embed(
                        "Processing Playlist",
                        f"Extracted {total_videos} links. Starting downloads...",
                        color=0x3498db
                    )
                    await status_msg.edit(embed=playlist_embed)

                if not self.voice_client or not self.voice_client.is_connected():
                    await self.join_voice_channel(ctx)

                if info['entries']:
                    first_entry = info['entries'][0]
                    if first_entry:
                        first_url = f"https://youtube.com/watch?v={first_entry['id']}"
                        first_song = await self.download_song(first_url, status_msg=None)
                        if first_song:
                            self.queue.append(first_song)
                            if not self.is_playing:
                                await self.play_next(ctx)

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
                            if not self.is_playing and not self.voice_client.is_playing():
                                await self.play_next(ctx)

            if status_msg:
                final_embed = self.create_embed(
                    "Playlist Complete",
                    f"All songs have been downloaded and queued",
                    color=0x00ff00
                )
                try:
                    await status_msg.edit(embed=final_embed)
                    await status_msg.delete(delay=5)
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
                            if not self.is_playing and not self.voice_client.is_playing():
                                await self.play_next(ctx)

            if status_msg:
                final_embed = self.create_embed(
                    "Playlist Complete",
                    f"All songs have been downloaded and queued",
                    color=0x00ff00
                )
                try:
                    await status_msg.edit(embed=final_embed)
                    await status_msg.delete(delay=5)
                except:
                    pass

        except Exception as e:
            print(f"Error in playlist download processing: {str(e)}")

    async def play(self, ctx, *, query=None):
        """Play a song in the voice channel"""
        try:
            if not query:
                usage_embed = self.create_embed(
                    "Usage",
                    "Usage: !play YouTube Link/Youtube Search/Spotify Link",
                    color=0xe74c3c
                )
                await ctx.send(embed=usage_embed)
                return

            if not ctx.author.voice:
                embed = self.create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c)
                await ctx.send(embed=embed)
                return

            if not ctx.guild.voice_client:
                await ctx.author.voice.channel.connect()
            elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
                await ctx.guild.voice_client.move_to(ctx.author.voice.channel)

            music_bot.voice_client = ctx.guild.voice_client

            processing_embed = self.create_embed(
                "Processing",
                f"Processing your request...",
                color=0x3498db
            )
            status_msg = await ctx.send(embed=processing_embed)

            if 'open.spotify.com' in query:
                result = await self.handle_spotify_url(query, ctx, status_msg)
                if not result:
                    return
            else:
                async with self.queue_lock:
                    result = await self.download_song(query, status_msg=status_msg, ctx=ctx)
                    if not result:
                        return

                    self.queue.append({
                        'title': result['title'],
                        'url': result['url'],
                        'file_path': result['file_path'],
                        'thumbnail': result.get('thumbnail'),
                        'ctx': ctx,
                        'is_stream': result.get('is_stream', False),
                        'is_from_playlist': result.get('is_from_playlist', False)
                    })

                    if not self.is_playing and not self.waiting_for_song:
                        await self.process_queue()
                    else:
                        if not result.get('is_from_playlist'):
                            queue_pos = len(self.queue)
                            queue_embed = self.create_embed(
                                "Added to Queue",
                                f"[🎵 {result['title']}]({result['url']})\nPosition in queue: {queue_pos}",
                                color=0x3498db,
                                thumbnail_url=result.get('thumbnail')
                            )
                            queue_msg = await ctx.send(embed=queue_embed)
                            self.queued_messages[result['url']] = queue_msg

        except Exception as e:
            error_msg = f"Error playing song: {str(e)}"
            print(error_msg)
            error_embed = self.create_embed("Error", error_msg, color=0xff0000)
            await ctx.send(embed=error_embed)

    async def after_playing_coro(self, error, ctx):
        """Coroutine called after a song finishes"""
        if error:
            print(f"Error in playback: {error}")
        
        print("Song finished playing, checking queue...")
        if len(self.queue) > 0:
            print(f"Queue length: {len(self.queue)}")
        if not self.download_queue.empty():
            print(f"Download queue size: {self.download_queue.qsize()}")
        
        if self.loop_mode and self.current_song:
            looped_song = self.current_song.copy()
            looped_song['has_played'] = True
            self.queue.insert(0, looped_song)
            print("Loop mode: Added current song back to queue")
        
        if not self.currently_downloading and not self.download_queue.empty():
            print("More songs in download queue, continuing processing...")
        
        if len(self.queue) == 0 and not self.download_queue.empty():
            print("Waiting for next song to finish downloading...")
            await asyncio.sleep(1)
            
        if len(self.queue) > 0 or not self.download_queue.empty():
            await self.play_next(ctx)
        else:
            print("All songs finished, updating activity...")
            if self.now_playing_message:
                try:
                    finished_embed = self.create_embed(
                        "Finished Playing",
                        f"[{self.current_song['title']}]({self.current_song['url']})",
                        color=0x808080,
                        thumbnail_url=self.current_song.get('thumbnail')
                    )
                    await self.now_playing_message.edit(embed=finished_embed)
                except Exception as e:
                    print(f"Error updating finished message: {str(e)}")
            
            self.is_playing = False
            self.current_song = None
            await self.update_activity()

    async def queue(self, ctx):
        """Display the current queue"""
        if not self.queue and not self.current_song:
            embed = self.create_embed("Queue Empty", "No songs in queue", color=0xe74c3c)
            await ctx.send(embed=embed)
            return
            
        queue_text = ""
        total_songs = len(self.queue)
        
        if self.current_song:
            status = "🔁 Now playing" if self.loop_mode else "▶️ Now playing"
            queue_text += f"{status}: [{self.current_song['title']}]({self.current_song['url']})\n\n"
        
        if self.queue:
            queue_text += "**Up Next:**\n"
            for i, song in enumerate(self.queue[:10], 1):
                queue_text += f"`{i}.` [{song['title']}]({song['url']})\n"
            
            if len(self.queue) > 10:
                queue_text += f"\n*...and {len(self.queue) - 10} more songs*"
        
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

    async def update_activity(self):
        """Update the bot's activity status"""
        await update_activity(self.bot, self.current_song, self.is_playing)

music_bot = None

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    global music_bot
    
    clear_downloads_folder()
    
    await bot.change_presence(activity=discord.Game(name="nothing! use !play "))
    print(f"------------------")
    print(f"Logged in as {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Bot Invite URL: {discord.utils.oauth_url(bot.user.id)}")
    print(f"------------------")
    print(f"Loaded configuration:")
    print(f"Owner ID: {OWNER_ID}")
    print(f"Command Prefix: {PREFIX}")
    print(f"------------------")
    
    # Load scripts and commands
    load_scripts()
    await load_commands(bot)
    update_checker.start(bot)
    
    if not music_bot:
        music_bot = MusicBot()
        await music_bot.setup(bot)

@bot.command(name='play')
async def play(ctx, *, query=None):
    """Play a song in the voice channel"""
    try:
        if not query:
            usage_embed = music_bot.create_embed(
                "Usage",
                "Usage: !play YouTube Link/Youtube Search/Spotify Link",
                color=0xe74c3c
            )
            await ctx.send(embed=usage_embed)
            return

        if not ctx.author.voice:
            embed = music_bot.create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c)
            await ctx.send(embed=embed)
            return

        if not ctx.guild.voice_client:
            await ctx.author.voice.channel.connect()
        elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
            await ctx.guild.voice_client.move_to(ctx.author.voice.channel)

        music_bot.voice_client = ctx.guild.voice_client

        processing_embed = music_bot.create_embed(
            "Processing",
            f"Processing your request...",
            color=0x3498db
        )
        status_msg = await ctx.send(embed=processing_embed)

        if 'open.spotify.com' in query:
            result = await music_bot.handle_spotify_url(query, ctx, status_msg)
            if not result:
                return
        else:
            async with music_bot.queue_lock:
                result = await music_bot.download_song(query, status_msg=status_msg, ctx=ctx)
                if not result:
                    return

                music_bot.queue.append({
                    'title': result['title'],
                    'url': result['url'],
                    'file_path': result['file_path'],
                    'thumbnail': result.get('thumbnail'),
                    'ctx': ctx,
                    'is_stream': result.get('is_stream', False),
                    'is_from_playlist': result.get('is_from_playlist', False)
                })

                if not music_bot.is_playing and not music_bot.waiting_for_song:
                    await music_bot.process_queue()
                else:
                    if not result.get('is_from_playlist'):
                        queue_pos = len(music_bot.queue)
                        queue_embed = music_bot.create_embed(
                            "Added to Queue",
                            f"[🎵 {result['title']}]({result['url']})\nPosition in queue: {queue_pos}",
                            color=0x3498db,
                            thumbnail_url=result.get('thumbnail')
                        )
                        queue_msg = await ctx.send(embed=queue_embed)
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
        if music_bot.voice_client and music_bot.voice_client.is_playing():
            music_bot.voice_client.pause()
            music_bot.last_activity = time.time()
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
        print(f"Error in pause command: {str(e)}")
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
        if music_bot.voice_client and music_bot.voice_client.is_paused():
            music_bot.voice_client.resume()
            music_bot.last_activity = time.time()
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
        print(f"Error in resume command: {str(e)}")
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
        music_bot.last_activity = time.time()
        await ctx.send(embed=music_bot.create_embed("Skipped", "Skipped the current song", color=0x3498db))
    else:
        await ctx.send(embed=music_bot.create_embed("Error", "Nothing is playing to skip", color=0xe74c3c))

@bot.command(name='queue', aliases=['playing'])
async def queue(ctx):
    """Show the current queue"""
    if not music_bot.queue and music_bot.download_queue.empty():
        await ctx.send(embed=music_bot.create_embed("Queue Empty", "No songs in queue", color=0xe74c3c))
        return

    queue_text = ""
    position = 1

    if music_bot.current_song:
        queue_text += "**Now Playing:**\n"
        queue_text += f"🎵 [{music_bot.current_song['title']}]({music_bot.current_song['url']})\n\n"

    if music_bot.queue:
        queue_text += "**Up Next:**\n"
        for song in music_bot.queue:
            queue_text += f"`{position}.` [{song['title']}]({song['url']})\n"
            position += 1

    if not music_bot.download_queue.empty():
        queue_text += "\n**Downloading:**\n"
        downloading_count = music_bot.download_queue.qsize()
        queue_text += f"🔄 {downloading_count} song(s) in download queue\n"

    embed = music_bot.create_embed(
        f"Music Queue - {len(music_bot.queue)} song(s)",
        queue_text if queue_text else "Queue is empty",
        color=0x3498db
    )
    await ctx.send(embed=embed)

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
    music_bot.loop_mode = not music_bot.loop_mode
    status = "enabled" if music_bot.loop_mode else "disabled"
    color = 0x2ecc71 if music_bot.loop_mode else 0xe74c3c
    
    await ctx.send(embed=music_bot.create_embed(f"Loop Mode {status.title()}", f"[🎵 {music_bot.current_song['title']}]({music_bot.current_song['url']}) will {'now' if music_bot.loop_mode else 'no longer'} be looped", color=color))

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

    embed = music_bot.create_embed(
        "Now Playing 🎵",
        f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})",
        color=0x3498db,
        thumbnail_url=music_bot.current_song.get('thumbnail')
    )

    await ctx.send(embed=embed)

bot.remove_command('help')

bot.run(os.getenv('DISCORD_TOKEN'))
