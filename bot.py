import os
import discord
import yt_dlp
import asyncio
import re
import unicodedata
import sys
import locale
import time
import shutil
import json
import pytz
import logging
import urllib.request
import subprocess
import spotipy
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pathlib import Path
from discord.ext import tasks
from collections import deque
from datetime import datetime
from pytz import timezone
from scripts.play_next import play_next
from scripts.ui_components import NowPlayingView
from scripts.process_queue import process_queue
from scripts.clear_queue import clear_queue
from scripts.format_size import format_size
from scripts.duration import get_audio_duration
from scripts.url_identifier import is_url, is_playlist_url, is_radio_stream
from scripts.handle_playlist import PlaylistHandler
from scripts.after_playing_coro import AfterPlayingHandler
from scripts.handle_spotify import SpotifyHandler
from scripts.config import load_config, YTDL_OPTIONS, FFMPEG_OPTIONS
from scripts.logging import setup_logging, get_ytdlp_logger
from scripts.updatescheduler import check_updates, update_checker
from scripts.voice import join_voice_channel, leave_voice_channel, handle_voice_state_update
from scripts.inactivity import start_inactivity_checker, check_inactivity
from scripts.messages import update_or_send_message, create_embed
from spotipy.oauth2 import SpotifyClientCredentials
from scripts.ytdlp import get_ytdlp_path, ytdlp_version
from scripts.ffmpeg import check_ffmpeg_in_path, install_ffmpeg_windows, install_ffmpeg_macos, install_ffmpeg_linux, get_ffmpeg_path
from scripts.cleardownloads import clear_downloads_folder
from scripts.restart import restart_bot
from scripts.load_commands import load_commands
from scripts.load_scripts import load_scripts
from scripts.activity import update_activity
from scripts.spotify import get_spotify_album_details, get_spotify_track_details, get_spotify_playlist_details

# Load environment variables
load_dotenv()

# Load configuration
config_vars = load_config()
OWNER_ID = config_vars['OWNER_ID']
PREFIX = config_vars['PREFIX']
LOG_LEVEL = config_vars['LOG_LEVEL']
INACTIVITY_TIMEOUT = config_vars['INACTIVITY_TIMEOUT']
AUTO_LEAVE_EMPTY = config_vars['AUTO_LEAVE_EMPTY']
DEFAULT_VOLUME = config_vars['DEFAULT_VOLUME']
AUTO_CLEAR_DOWNLOADS = config_vars['AUTO_CLEAR_DOWNLOADS']
SHOW_PROGRESS_BAR = config_vars['SHOW_PROGRESS_BAR']

#Set up colors
GREEN = '\033[92m'
BLUE = '\033[94m'
RED = '\033[91m'
RESET = '\033[0m'

# Set up logging
setup_logging(LOG_LEVEL)

YTDLP_PATH = get_ytdlp_path()
FFMPEG_PATH = get_ffmpeg_path()

DOWNLOADS_DIR = Path(__file__).parent / 'downloads'
OWNER_ID = OWNER_ID

if not DOWNLOADS_DIR.exists():
    DOWNLOADS_DIR.mkdir()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True,
    owner_id=int(OWNER_ID)
)

@bot.event
async def on_command_error(ctx, error):
    print(f"Error in command {ctx.command}: {str(error)}")
    await ctx.send(
        embed=create_embed(
            "Error",
            f"Error: {str(error)}",
            color=0xe74c3c,
            ctx=ctx
        )
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Error: {str(error)}")

@bot.event
async def on_voice_state_update(member, before, after):
    """Event handler for voice state updates"""
    global music_bot
    await handle_voice_state_update(music_bot, member, before, after)

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
                    color=0xf1c40f,
                    timestamp=datetime.now()
                )
                
                await self.status_msg.edit(embed=embed)               
            except Exception as e:
                print(f"Error updating progress: {str(e)}")

class MusicBot(PlaylistHandler, AfterPlayingHandler, SpotifyHandler):
    def __init__(self):
        """Initialize the music bot"""
        self.queue = []
        self.current_song = None
        self.is_playing = False
        self.voice_client = None
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
        self.downloads_dir = Path(__file__).parent / 'downloads'
        self.cookie_file = Path(__file__).parent / 'cookies.txt'
        self.playback_start_time = None  # Track when the current song started playing      
        if not self.downloads_dir.exists():
            self.downloads_dir.mkdir()
        self.last_activity = time.time()
        self.inactivity_timeout = INACTIVITY_TIMEOUT
        self.inactivity_leave = config_vars.get('INACTIVITY_LEAVE', True)
        self._inactivity_task = None
        self.last_update = 0
        self._last_progress = -1
        self.last_known_ctx = None
        self.bot = None
        self.was_skipped = False  # Add flag to track if song was skipped

        load_dotenv(dotenv_path=".spotifyenv")
        client_id = os.getenv('SPOTIPY_CLIENT_ID')
        client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        
        print(f"{GREEN}Spotify environment file path:{RESET} {BLUE}{os.path.abspath('.spotifyenv')}{RESET}")
        print(f"{GREEN}Spotify client ID found:{RESET} {BLUE if client_id else RED}{'Yes' if client_id else 'No'}{RESET}")
        print(f"{GREEN}Spotify client secret found:{RESET} {BLUE if client_secret else RED}{'Yes' if client_secret else 'No'}{RESET}")
        
        if not client_id or not client_secret:
            print(f"{RED}Warning: Spotify credentials not found. Spotify functionality will be limited.{RESET}")
            self.sp = None
        else:
            try:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=client_id,
                    client_secret=client_secret
                )
                self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
                print(f"{GREEN}Successfully initialized Spotify client{RESET}")
            except Exception as e:
                print(f"{RED}Error initializing Spotify client: {str(e)}{RESET}")
                self.sp = None

    async def setup(self, bot_instance):
        """Setup the bot with the event loop"""
        self.bot = bot_instance
        self.bot_loop = asyncio.get_event_loop()
        await self.start_command_processor()
        await start_inactivity_checker(self)
        asyncio.create_task(self.process_download_queue())
        
        # Add the persistent view
        self.bot.add_view(NowPlayingView())

    async def start_command_processor(self):
        """Start the command processor task"""
        if self.command_processor_task is None:
            self.command_processor_task = asyncio.create_task(self.process_command_queue())
            print('----------------------------------------')

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
                    error_embed = create_embed("Error", f"Failed to process command: {str(e)}", color=0xe74c3c, ctx=ctx)
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
        processing_embed = create_embed(
            "Processing",
            f"Searching for {query}",
            color=0x3498db,
            ctx=ctx
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
                                error_embed = create_embed("Error", "Failed to download song", color=0xe74c3c, ctx=ctx)
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
                                playlist_embed = create_embed(
                                    "Adding Playlist",
                                    f"Adding {len(result['entries'])} songs to queue...",
                                    color=0x3498db,
                                    ctx=ctx
                                )
                                await status_msg.edit(embed=playlist_embed)

                        if self.voice_client and self.voice_client.is_playing():
                            self.queue.append(result)
                            if not result.get('is_from_playlist'):
                                queue_embed = create_embed(
                                    "Added to Queue 🎵", 
                                    f"[ {result['title']}]({result['url']})",
                                    color=0x3498db,
                                    thumbnail_url=result.get('thumbnail'),
                                    ctx=ctx
                                )
                                queue_msg = await ctx.send(embed=queue_embed)
                                self.queued_messages[result['url']] = queue_msg
                        else:
                            self.queue.append(result)
                            await play_next(ctx)

                except Exception as e:
                    print(f"Error processing download: {str(e)}")
                    if not status_msg:
                        error_embed = create_embed("Error", f"Error processing: {str(e)}", color=0xe74c3c, ctx=ctx)
                        await self.update_or_send_message(ctx, error_embed)
                
                finally:
                    self.currently_downloading = False
                    self.download_queue.task_done()

            except Exception as e:
                print(f"Error in download queue processor: {str(e)}")
                await asyncio.sleep(1)

    def create_progress_bar(self, percentage, length=10):
        """Create a progress bar with the given percentage"""
        filled = int(length * (percentage / 100))
        bar = '█' * filled + '░' * (length - filled)
        return f"[{bar}] {percentage}%"

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
                        
                        total_size = format_size(total)
                        
                        try:
                            await status_msg.fetch()
                            description = "Downloading..."
                            if SHOW_PROGRESS_BAR:
                                progress_bar = self.create_progress_bar(percentage)
                                description += f"\n{progress_bar}"
                            description += f"\nFile size: {total_size}"
                            
                            processing_embed = create_embed(
                                "Processing",
                                description,
                                color=0x3498db,
                                ctx=status_msg.channel
                            )
                            await status_msg.edit(embed=processing_embed)
                        except discord.NotFound:
                            return
                        except Exception as e:
                            print(f"Error updating progress message: {str(e)}")
                            return
            except Exception as e:
                print(f"Error in progress hook: {str(e)}")

    async def download_song(self, query, status_msg=None, ctx=None):
        """Download a song from YouTube, Spotify, or handle radio stream"""
        try:
            self._last_progress = -1

            if is_playlist_url(query):
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
                                embed=create_embed(
                                    "Error",
                                    "Could not retrieve details from Spotify URL.",
                                    color=0xe74c3c,
                                    ctx=status_msg.channel
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

            if is_radio_stream(query):
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
                            embed=create_embed(
                                "Error",
                                f"Failed to process radio stream: {str(e)}",
                                color=0xe74c3c,
                                ctx=status_msg.channel
                            )
                        )
                    return None

            if not self.downloads_dir.exists():
                self.downloads_dir.mkdir()

            if not is_url(query):
                query = f"ytsearch1:{query}"

            ydl_opts = {
                **YTDL_OPTIONS,
                'outtmpl': os.path.join(self.downloads_dir, '%(id)s.%(ext)s'),
                'cookiefile': self.cookie_file if self.cookie_file.exists() else None,
                'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(
                    self.progress_hook(d, status_msg), 
                    self.bot_loop
                )] if status_msg else [],
                'default_search': 'ytsearch'
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # Single extraction with download
                    info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(query, download=True))
                    
                    if info.get('_type') == 'playlist' and not is_playlist_url(query):
                        # Handle search results that return a playlist
                        if not info.get('entries'):
                            raise Exception("No search results found")
                        info = info['entries'][0]
                        file_path = os.path.join(self.downloads_dir, f"{info['id']}.{info.get('ext', 'opus')}")
                    
                    elif info.get('_type') == 'playlist' and is_playlist_url(query):
                        # Handle actual playlist URLs
                        if not info.get('entries'):
                            raise Exception("Playlist is empty")

                        ctx = ctx or status_msg.channel if status_msg else None
                        first_video = info['entries'][0]
                        video_thumbnail = first_video.get('thumbnail')
                        playlist_title = info.get('title', 'Unknown Playlist')
                        playlist_url = info.get('webpage_url', query)
                        total_videos = len(info['entries'])

                        if status_msg:
                            playlist_embed = create_embed(
                                "Adding Playlist 🎵",
                                f"[ {playlist_title}]({playlist_url})\nDownloading first song...",
                                color=0x3498db,
                                thumbnail_url=video_thumbnail,
                                ctx=ctx
                            )
                            await status_msg.edit(embed=playlist_embed)

                        if info['entries']:
                            first_entry = info['entries'][0]
                            if not first_entry:
                                raise Exception("Failed to get first video from playlist")

                            first_file_path = os.path.join(self.downloads_dir, f"{first_entry['id']}.{first_entry.get('ext', 'opus')}")

                            first_song = {
                                'title': first_entry['title'],
                                'url': first_entry['webpage_url'] if first_entry.get('webpage_url') else first_entry['url'],
                                'file_path': first_file_path,
                                'thumbnail': first_entry.get('thumbnail'),
                                'ctx': ctx,
                                'is_from_playlist': True,
                                'requester': ctx.author if ctx else None  # Add requester information
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
                        # Handle single video
                        file_path = os.path.join(self.downloads_dir, f"{info['id']}.{info.get('ext', 'opus')}")
                
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
                            print(f"Note: Could not delete processing message: {e}")
                    
                    return {
                        'title': info['title'],
                        'url': info['webpage_url'] if info.get('webpage_url') else info['url'],
                        'file_path': file_path,
                        'thumbnail': info.get('thumbnail'),
                        'is_stream': False,
                        'is_from_playlist': is_playlist_url(query),
                        'ctx': status_msg.channel if status_msg else None
                    }
                except Exception as e:
                    print(f"Error downloading song: {str(e)}")
                    if status_msg:
                        error_embed = create_embed("Error", f"Error downloading song: {str(e)}", color=0xff0000, ctx=status_msg.channel)
                        await status_msg.edit(embed=error_embed)
                    raise

        except Exception as e:
            print(f"Error downloading song: {str(e)}")
            if status_msg:
                error_embed = create_embed("Error", f"Error downloading song: {str(e)}", color=0xff0000, ctx=status_msg.channel)
                await status_msg.edit(embed=error_embed)
            raise

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
    print(f"----------------------------------------")
    print(f"{GREEN}Logged in as {RESET}{BLUE}{bot.user.name}")
    print(f"{GREEN}Bot ID: {RESET}{BLUE}{bot.user.id}")
    print(f"{GREEN}Bot Invite URL: {RESET}{BLUE}{discord.utils.oauth_url(bot.user.id)}")
    print(f"----------------------------------------")
    print(f"{GREEN}Loaded configuration:{RESET}")
    print(f"{GREEN}Owner ID:{RESET} {BLUE}{OWNER_ID}{RESET} ")
    print(f"{GREEN}Command Prefix:{RESET} {BLUE}{PREFIX}{RESET} ")
    
    # Load scripts and commands
    load_scripts()
    await load_commands(bot)
    update_checker.start(bot)
    
    if not music_bot:
        music_bot = MusicBot()
        await music_bot.setup(bot)

bot.remove_command('help')
bot.run(os.getenv('DISCORD_TOKEN'))