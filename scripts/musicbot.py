import aiohttp
import asyncio
import discord
import json
import locale
import logging
import os
import pytz
import re
import shutil
import spotipy
import subprocess
import sys
import time
import unicodedata
import urllib.request
import yt_dlp
from collections import deque
from datetime import datetime
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pathlib import Path
from pytz import timezone
from urllib.parse import urlparse
from scripts.constants import RED, GREEN, BLUE, RESET, YELLOW
from scripts.activity import update_activity
from scripts.after_playing_coro import AfterPlayingHandler
from scripts.cleardownloads import clear_downloads_folder
from scripts.clear_queue import clear_queue
from scripts.config import load_config, YTDL_OPTIONS, FFMPEG_OPTIONS, BASE_YTDL_OPTIONS, COOKIES_PATH
from scripts.downloadprogress import DownloadProgress
from scripts.duration import get_audio_duration
from scripts.format_size import format_size
from scripts.handle_playlist import PlaylistHandler
from scripts.handle_spotify import SpotifyHandler
from scripts.inactivity import start_inactivity_checker, check_inactivity
from scripts.load_commands import load_commands
from scripts.load_scripts import load_scripts
from scripts.logging import setup_logging, get_ytdlp_logger, CachedVideoFound
from scripts.messages import update_or_send_message, create_embed
from scripts.play_next import play_next
from scripts.process_queue import process_queue
from scripts.restart import restart_bot
from scripts.spotify import get_spotify_album_details, get_spotify_track_details, get_spotify_playlist_details
from scripts.ui_components import NowPlayingView
from scripts.updatescheduler import check_updates, update_checker
from scripts.url_identifier import is_url, is_playlist_url, is_radio_stream, is_youtube_channel
from scripts.voice import join_voice_channel, leave_voice_channel, handle_voice_state_update
from scripts.ytdlp import get_ytdlp_path, ytdlp_version
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.cache_handler import CacheFileHandler
from scripts.caching import playlist_cache

# Load configuration variables from config.json
config_vars = load_config()
# Set default inactivity timeout to 60 seconds if not specified in config
INACTIVITY_TIMEOUT = config_vars.get('INACTIVITY_TIMEOUT', 60)  # Default to 60 seconds if not specified

class MusicBot(PlaylistHandler, AfterPlayingHandler, SpotifyHandler):
    """
    Main music bot class that handles audio playback and queue management.
    Inherits from PlaylistHandler, AfterPlayingHandler, and SpotifyHandler
    to organize functionality into logical components.
    """
    _instances = {}  # Dictionary to store server-specific instances
    _credentials_shown = False  # Class variable to track if credentials have been shown

    @classmethod
    def get_instance(cls, guild_id):
        """
        Get or create a server-specific music bot instance.
        This implements the singleton pattern per guild to ensure
        each server has its own isolated music queue and state.
        """
        if guild_id not in cls._instances:
            # Never show credentials automatically - we'll do it explicitly in on_ready
            cls._instances[guild_id] = cls(show_credentials=False)
            # Set the guild_id for this instance
            cls._instances[guild_id].guild_id = guild_id
            
            # If we have a setup instance with a bot reference, copy it to the new instance
            if 'setup' in cls._instances and cls._instances['setup'].bot:
                cls._instances[guild_id].bot = cls._instances['setup'].bot
                
            # Ensure bot_loop is initialized
            if not cls._instances[guild_id].bot_loop:
                cls._instances[guild_id].bot_loop = asyncio.get_event_loop()
                
        return cls._instances[guild_id]

    def __init__(self, show_credentials=False):
        """
        Initialize the music bot with default values.
        
        Args:
            show_credentials (bool): Whether to show credential status messages
        """
        # Discord bot instance (set later)
        self.bot = None
        self.guild_id = None  # Will be set when get_instance is called
        self.queue = []  # Song queue for this server
        self.current_song = None  # Currently playing song
        self.is_playing = False  # Whether audio is currently playing
        self.voice_client = None  # Voice client connection
        self.waiting_for_song = False  # Flag to indicate waiting for a song to download
        self.queue_lock = asyncio.Lock()  # Lock to prevent race conditions when modifying queue
        self.download_queue = asyncio.Queue()  # Queue for songs to be downloaded for this server
        self.currently_downloading = False  # Flag to indicate if a download is in progress
        self.command_queue = asyncio.Queue()  # Queue for commands to be processed
        self.command_processor_task = None  # Task for processing commands
        self.download_lock = asyncio.Lock()  # Lock to prevent concurrent downloads
        self.bot_loop = None  # Event loop for async operations
        self.queued_messages = {}  # Messages shown when songs are queued
        self.current_command_msg = None  # Current command message
        self.current_command_author = None  # User who issued the current command
        self.status_messages = {}  # Status messages for various operations
        self.now_playing_message = None  # Message showing currently playing song
        self.downloads_dir = Path(__file__).parent.parent / 'downloads'  # Directory for downloaded files
        self.playback_start_time = None  # Track when the current song started playing
        self.in_progress_downloads = {}  # Track downloads in progress for this server
        if not self.downloads_dir.exists():
            self.downloads_dir.mkdir()
        self.last_activity = time.time()  # Timestamp of last user interaction
        self.inactivity_timeout = INACTIVITY_TIMEOUT  # Seconds of inactivity before bot leaves
        self.inactivity_leave = config_vars.get('INACTIVITY_LEAVE', True)  # Whether to leave on inactivity
        self._inactivity_task = None  # Task for checking inactivity
        self.last_update = 0  # Timestamp of last progress update
        self._last_progress = -1  # Last download progress percentage
        self.last_known_ctx = None  # Last command context for fallback
        self.was_skipped = False  # Flag to track if song was skipped
        self.cache_dir = Path(__file__).parent.parent / '.cache'  # Directory for cache files
        self.spotify_cache = self.cache_dir / 'spotify'  # Directory for Spotify cache
        self.current_download_task = None  # Track current download task for this server
        self.current_ydl = None  # Track current YoutubeDL instance for this server
        self.should_stop_downloads = False  # Flag to control download cancellation for this server
        self.duration_cache = {}  # Cache for storing audio durations
        
        # Create cache directories if they don't exist
        self.cache_dir.mkdir(exist_ok=True)
        self.spotify_cache.mkdir(exist_ok=True)

        # Load Spotify API credentials from environment file
        load_dotenv(dotenv_path=".spotifyenv")
        client_id = os.getenv('SPOTIPY_CLIENT_ID')
        client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        
        # Initialize Spotify client if credentials are available
        if not client_id or not client_secret:
            if show_credentials:
                print(f"{RED}Warning: Spotify credentials not found. Spotify functionality will be unavailable.{RESET}")
                print(f"{BLUE}https://developer.spotify.com/documentation/web-api/concepts/apps{RESET}")
                print(f"{BLUE}Update your {RESET}{YELLOW}.spotifyenv file{RESET}\n")
            self.sp = None
        else:
            try:
                # Setup Spotify client with token caching
                cache_handler = CacheFileHandler(
                    cache_path=str(self.spotify_cache / '.spotify-token-cache')
                )
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=client_id,
                    client_secret=client_secret,
                    cache_handler=cache_handler
                )
                self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            except Exception as e:
                if show_credentials:
                    print(f"{RED}Error initializing Spotify client: {str(e)}{RESET}")
                self.sp = None

        # We'll skip showing YouTube and Genius credentials here
        # They will be shown when show_credentials() is called

        # Bind voice methods from external module
        self.join_voice_channel = lambda ctx: join_voice_channel(self, ctx)
        self.leave_voice_channel = lambda: leave_voice_channel(self)

    async def setup(self, bot_instance):
        """
        Setup the bot with the event loop and initialize necessary components.
        
        Args:
            bot_instance: The Discord bot instance to associate with this music bot
        """
        # Store the bot instance for later use
        self.bot = bot_instance
        self.bot_loop = asyncio.get_event_loop()
        await self.start_command_processor()
        await start_inactivity_checker(self)
        asyncio.create_task(self.process_download_queue())
        self.bot.add_view(NowPlayingView())

    async def start_command_processor(self):
        """
        Start the command processor task
        
        This method initializes the command processor task if it doesn't already exist.
        The command processor is responsible for handling all music commands in the background,
        ensuring they are processed sequentially and don't block the main bot execution.
        
        It also prints the location of the config file for reference during startup.
        """
        if self.command_processor_task is None:
            self.command_processor_task = asyncio.create_task(self.process_command_queue())
        
        # Config file
        print(f"{GREEN}Config file location:{RESET} {BLUE}{Path(__file__).parent.parent / 'config.json'}{RESET}")

    async def process_command_queue(self):
        """
        Process commands from the queue one at a time.
        
        This is an infinite loop that waits for commands to be added to the queue,
        then processes them in order. It handles errors gracefully to prevent
        the task from crashing.
        """
        while True:
            try:
                # Wait for a command to be added to the queue
                command_info = await self.command_queue.get()
                self.last_activity = time.time()
                ctx, query = command_info
                print(f"Processing command: {load_config()['PREFIX']}play {query}")

                try:
                    # Process the play command
                    await self._handle_play_command(ctx, query)
                except Exception as e:
                    # Handle errors in command processing
                    print(f"Error processing command: {e}")
                    error_embed = create_embed("Error", f"Failed to process command: {str(e)}", color=0xe74c3c, ctx=ctx)
                    await self.update_or_send_message(ctx, error_embed)
                finally:
                    # Mark the command as done
                    self.command_queue.task_done()
            except Exception as e:
                # Handle errors in the command processor itself
                print(f"Error in command processor: {str(e)}")
                await asyncio.sleep(1)

    async def _handle_play_command(self, ctx, query):
        """
        Internal method to handle a single play command.
        
        This method:
        1. Joins the voice channel if not already joined
        2. Checks if the query is already being downloaded
        3. Sends a processing message
        4. Adds the query to the download queue
        
        Args:
            ctx: The command context
            query: The search query or URL to play
        """
        # Reset the explicitly_stopped flag when a new play command is issued
        if hasattr(self, 'explicitly_stopped'):
            self.explicitly_stopped = False
        # Join voice channel if not already in one
        if not ctx.voice_client and not await self.join_voice_channel(ctx):
            raise Exception("Could not join voice channel")
        self.last_activity = time.time()

        # Check if this query is already being downloaded
        if query in self.in_progress_downloads:
            print(f"Query '{query}' already downloading - queueing duplicate request")
            if self.in_progress_downloads[query]:  # If we have the song info
                song_info = self.in_progress_downloads[query]
                self.queue.append(song_info)
                queue_embed = create_embed(
                    "Added to Queue 🎵", 
                    f"[ {song_info['title']}]({song_info['url']})",
                    color=0x3498db,
                    thumbnail_url=song_info.get('thumbnail'),
                    ctx=ctx
                )
                queue_msg = await ctx.send(embed=queue_embed)
                self.queued_messages[song_info['url']] = queue_msg
            return

        # Create and send a processing embed
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
        """
        Process the download queue sequentially.
        
        This is an infinite loop that waits for downloads to be added to the queue,
        then processes them in order. It handles errors gracefully to prevent
        the task from crashing.
        """
        while True:
            try:
                # Wait for a download to be added to the queue
                download_info = await self.download_queue.get()               
                query = download_info['query']
                ctx = download_info['ctx']
                status_msg = download_info['status_msg']

                # Skip processing if cache checking is stopped
                if not playlist_cache._should_continue_check:
                    self.download_queue.task_done()
                    continue

                try:
                    async with self.download_lock:
                        self.currently_downloading = True
                        print(f"Starting download: {query}")
                        self.in_progress_downloads[query] = None  # Mark as downloading but no info yet
                        
                        # Skip if cache checking is stopped
                        if not playlist_cache._should_continue_check:
                            self.download_queue.task_done()
                            continue
                            
                        result = await self.download_song(query, status_msg=status_msg, ctx=ctx)
                        if result:
                            self.in_progress_downloads[query] = result  # Store the song info
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
                    if status_msg:
                        error_embed = create_embed(
                            "Error ❌",
                            str(e),
                            color=0xe74c3c,
                            ctx=ctx if ctx else status_msg.channel
                        )
                        await status_msg.edit(embed=error_embed)
                    return None
                finally:
                    self.currently_downloading = False
                    self.download_queue.task_done()
            except Exception as e:
                print(f"Error in download queue processor: {str(e)}")
                await asyncio.sleep(1)

    async def cancel_downloads(self, disconnect_voice=True):
        """
        Cancel all active downloads and clear the download queue for this server
        
        This method safely cancels any ongoing downloads, clears the download queue,
        and optionally disconnects from the voice channel. It's used when the bot
        needs to stop all music-related activities, such as when a user issues a stop
        command or when the bot is shutting down.
        
        The method performs the following steps:
        1. Sets a flag to stop any active downloads for this server
        2. Cancels the current download task for this server if one exists
        3. Closes the current yt-dlp instance for this server
        4. Clears the download queue for this server
        5. Removes incomplete downloads from the queue
        6. Clears the in-progress downloads tracking for this server
        7. Stops any current playback
        8. Optionally disconnects from voice
        
        Args:
            disconnect_voice (bool): Whether to disconnect from voice chat after canceling downloads
            
        Returns:
            bool: True if the operation was successful
        """
        self.should_stop_downloads = True
        
        # Cancel current download task if it exists
        if self.current_download_task and not self.current_download_task.done():
            self.current_download_task.cancel()
            try:
                await self.current_download_task
            except (asyncio.CancelledError, Exception):
                pass

        # Force close current yt-dlp instance if it exists
        if self.current_ydl:
            try:
                # Try to abort the current download
                if hasattr(self.current_ydl, '_download_retcode'):
                    self.current_ydl._download_retcode = 1
                # Close the instance
                self.current_ydl.close()
            except Exception as e:
                print(f"Error closing yt-dlp instance: {e}")
        
        # Clear the download queue for this server
        while not self.download_queue.empty():
            try:
                self.download_queue.get_nowait()
                self.download_queue.task_done()
            except asyncio.QueueEmpty:
                break
                
        # Clear any incomplete downloads from the queue
        self.queue = [song for song in self.queue if not isinstance(song.get('file_path'), type(None))]
        
        # Clear in-progress downloads tracking for this server
        self.in_progress_downloads.clear()
        
        # Wait a moment for any active downloads to notice the cancellation flag
        await asyncio.sleep(0.5)
        self.should_stop_downloads = False
        self.current_download_task = None
        self.current_ydl = None

        # Stop any current playback
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        
        # Clear the queue and disconnect if requested
        self.queue.clear()
        if disconnect_voice:
            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.disconnect()
            
            # Reset the music bot state
            self.current_song = None
            self.is_playing = False
            if self.bot:
                await update_activity(self.bot, self.current_song, self.is_playing)

    def _download_hook(self, d):
        """
        Custom download hook that checks for cancellation
        
        This function is passed to yt-dlp as a progress callback. It checks if the 
        download should be cancelled and raises an exception if so, which will be 
        caught by the download process.
        
        Args:
            d (dict): The download progress information dictionary from yt-dlp
            
        Returns:
            dict: The same dictionary that was passed in
            
        Raises:
            Exception: If the download has been cancelled
        """
        if self.should_stop_downloads:
            raise Exception("Download cancelled by user")
        return d

    def create_progress_bar(self, percentage, length=10):
        """
        Create a progress bar with the given percentage
        
        This utility function generates a visual progress bar using Unicode block 
        characters, which is used to display download progress in Discord messages.
        
        Args:
            percentage (float): The percentage of completion (0-100)
            length (int, optional): The length of the progress bar in characters. Defaults to 10.
            
        Returns:
            str: A formatted progress bar string with percentage
        """
        filled = int(length * (percentage / 100))
        bar = '█' * filled + '░' * (length - filled)
        return f"[{bar}] {percentage}%"

    async def download_song(self, query, status_msg=None, ctx=None, skip_url_check=False):
        """
        Download a song from YouTube, Spotify, or handle radio stream
        
        This is a core function that handles the downloading and processing of media from
        various sources. It performs the following key operations:
        1. Checks for cached content to avoid redundant downloads
        2. Validates URLs and rejects unsupported content (like YouTube channels)
        3. Handles different media sources (YouTube, Spotify, radio streams)
        4. Updates Discord status messages with download progress
        5. Processes playlists when detected
        6. Manages download errors and retries
        
        The function supports various media sources:
        - YouTube videos and playlists
        - Spotify tracks, albums, and playlists
        - Direct audio stream URLs
        - Search queries (converted to YouTube searches)
        
        Args:
            query (str): The URL or search query to download
            status_msg (discord.Message, optional): Discord message to update with progress
            ctx (discord.Context, optional): Command context for sending messages
            skip_url_check (bool, optional): Whether to skip URL validation
            
        Returns:
            dict: Information about the downloaded song, or None if download failed
            
        Raises:
            Various exceptions that are caught and handled within the function
        """
        # Skip if cache checking is stopped
        if not playlist_cache._should_continue_check:
            return None

        if not skip_url_check and is_url(query):
            if is_youtube_channel(query):
                # Extract channel ID
                channel_id = None
                
                # Handle different channel URL formats
                if '/channel/UC' in query:
                    # Format: youtube.com/channel/UC...
                    channel_id = query.split('/channel/UC')[1].split('/')[0].split('?')[0]
                elif '/@' in query or '/c/' in query or '/user/' in query:
                    # Format: youtube.com/@username, youtube.com/c/username, or youtube.com/user/username
                    # Extract the channel ID directly using yt-dlp's channel_id field
                    
                    # First try with a simple approach for handle-based URLs
                    if '/@' in query:
                        username = query.split('/@')[1].split('/')[0].split('?')[0]
                        # Try a direct conversion to a playlist URL for the most common case
                        playlist_url = f"https://www.youtube.com/@{username}/videos"
                        
                        # Handle as a playlist
                        await self._handle_playlist(playlist_url, ctx, status_msg)
                        return None
                    
                    # For other formats, try to extract the channel ID
                    with yt_dlp.YoutubeDL({
                        'quiet': True,
                        'extract_flat': True,
                        'skip_download': True,
                        'socket_timeout': 5  # 5 second timeout
                    }) as ydl:
                        try:
                            # Use asyncio.wait_for to add a timeout
                            channel_info = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(query, download=False)),
                                timeout=10  # 10 second timeout
                            )
                            if channel_info and channel_info.get('channel_id'):
                                # The channel_id already includes the 'UC' prefix
                                channel_id = channel_info.get('channel_id')[2:] if channel_info.get('channel_id').startswith('UC') else channel_info.get('channel_id')
                        except asyncio.TimeoutError:
                            # Try a fallback for handle-based URLs
                            if '/@' in query:
                                username = query.split('/@')[1].split('/')[0].split('?')[0]
                                playlist_url = f"https://www.youtube.com/@{username}/videos"
                                
                                if status_msg:
                                    await status_msg.edit(embed=create_embed(
                                        "Channel Detected",
                                        f"Found channel @{username}. Processing videos...",
                                        color=0x3498db,
                                        ctx=ctx
                                    ))
                                    
                                    # Handle as a playlist
                                    await self._handle_playlist(playlist_url, ctx, status_msg)
                                    return None
                        except Exception as e:
                            # Error extracting channel ID, continue with normal processing
                            pass
                
                if channel_id:
                    # Convert to playlist URL
                    playlist_url = f"https://www.youtube.com/playlist?list=UU{channel_id}"
                    
                    if status_msg:
                        channel_name = query.split('/')[-1] if '/' in query else query
                        await status_msg.edit(embed=create_embed(
                            "Channel Detected",
                            f"Found channel {channel_name}. Processing as a playlist...",
                            color=0x3498db,
                            ctx=ctx
                        ))
                    
                    # Handle as a playlist
                    await self._handle_playlist(playlist_url, ctx, status_msg)
                    return None
                else:
                    # If we couldn't extract the channel ID, show an error
                    if status_msg:
                        await status_msg.edit(embed=create_embed(
                            "Error",
                            "Could not process this channel. Please try a specific video URL instead.",
                            color=0xe74c3c,
                            ctx=ctx
                        ))
                    return None

        try:
            # Check cache first for YouTube videos
            if 'youtube.com/watch' in query or 'youtu.be/' in query:
                video_id = None
                if 'youtube.com/watch' in query:
                    video_id = query.split('watch?v=')[1].split('&')[0]
                elif 'youtu.be/' in query:
                    video_id = query.split('youtu.be/')[1].split('?')[0]
                
                if video_id:
                    # Check if video is blacklisted
                    if playlist_cache.is_blacklisted(video_id):
                        print(f"{RED}Unavailable video: {video_id}{RESET}")
                        if status_msg:
                            await status_msg.edit(embed=create_embed(
                                "Skipped ⚠️",
                                "This video was previously marked as unavailable.",
                                color=0xe74c3c,
                                ctx=ctx
                            ))
                            try:
                                await status_msg.delete(delay=10)
                            except discord.NotFound:
                                print(f"Note: Status message already deleted")
                            except Exception as e:
                                print(f"Note: Could not delete status message: {e}")
                        return None
                        
                    cached_info = playlist_cache.get_cached_info(video_id)
                    if cached_info and os.path.exists(cached_info['file_path']):
                        print(f"{GREEN}Found cached YouTube file: {RESET}{BLUE}{video_id} - {cached_info.get('title', 'Unknown')}{RESET}")
                        if status_msg:
                            try:
                                await status_msg.delete()
                            except discord.NotFound:
                                print(f"Note: Status message already deleted")
                            except Exception as e:
                                print(f"Note: Could not delete processing message: {e}")
                        return {
                            'title': cached_info.get('title', 'Unknown'),  # Use cached title
                            'url': query,
                            'file_path': cached_info['file_path'],
                            'thumbnail': cached_info.get('thumbnail'),
                            'is_stream': False,
                            'is_from_playlist': is_playlist_url(query),
                            'ctx': status_msg.channel if status_msg else None,
                            'is_from_cache': True
                        }

            # Check cache by title for search queries (non-URLs)
            if not is_url(query):
                # Check if query is a YouTube video ID (11 characters, alphanumeric + - and _)
                if len(query) == 11 and all(c.isalnum() or c in '-_' for c in query):
                    # This looks like a YouTube video ID, search cache directly by ID
                    cached_info = playlist_cache.get_cached_info(query)
                    if cached_info and os.path.exists(cached_info['file_path']):
                        print(f"{GREEN}Found cached file by video ID: {RESET}{BLUE}{query} - {cached_info.get('title', 'Unknown')}{RESET}")
                        if status_msg:
                            try:
                                await status_msg.delete()
                            except discord.NotFound:
                                print(f"Note: Status message already deleted")
                            except Exception as e:
                                print(f"Note: Could not delete processing message: {e}")
                        return {
                            'title': cached_info.get('title', 'Unknown'),
                            'url': f"https://www.youtube.com/watch?v={query}",
                            'file_path': cached_info['file_path'],
                            'thumbnail': cached_info.get('thumbnail'),
                            'is_stream': False,
                            'is_from_playlist': False,
                            'ctx': status_msg.channel if status_msg else None,
                            'is_from_cache': True
                        }
                
                # If not a video ID, try searching by title
                cached_by_title = playlist_cache.find_cached_by_title(query)
                if cached_by_title and os.path.exists(cached_by_title['file_path']):
                    print(f"{GREEN}Found cached file by title: {RESET}{BLUE}{cached_by_title.get('id', 'Unknown')} - {cached_by_title.get('title', 'Unknown')}{RESET}")
                    if status_msg:
                        try:
                            await status_msg.delete()
                        except discord.NotFound:
                            print(f"Note: Status message already deleted")
                        except Exception as e:
                            print(f"Note: Could not delete processing message: {e}")
                    return {
                        'title': cached_by_title.get('title', 'Unknown'),
                        'url': f"https://www.youtube.com/watch?v={cached_by_title.get('id', '')}" if cached_by_title.get('id') else query,
                        'file_path': cached_by_title['file_path'],
                        'thumbnail': cached_by_title.get('thumbnail'),
                        'is_stream': False,
                        'is_from_playlist': False,
                        'ctx': status_msg.channel if status_msg else None,
                        'is_from_cache': True
                    }

            # If not in cache or not a YouTube video, proceed with normal download
            self._last_progress = -1
            if not skip_url_check:
                if is_playlist_url(query):
                    ctx = (ctx or status_msg.channel) if status_msg else None
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
                                # Set requester information for each track
                                song_info['requester'] = ctx.author if ctx else None
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
                                # Set requester information for each track
                                song_info['requester'] = ctx.author if ctx else None
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
                
            # Create DownloadProgress instance with ctx
            progress = DownloadProgress(status_msg, None)
            progress.title = query if not is_url(query) else ""
            progress.ctx = ctx
            
            # Initialize the progress updater
            try:
                progress.start_updater(self.bot_loop)
            except Exception as e:
                print(f"Error starting progress updater: {e}")
            
            # Configure yt-dlp options with progress hooks
            ytdl_opts = YTDL_OPTIONS.copy()
            ytdl_opts['progress_hooks'] = [progress.progress_hook]
            
            async def extract_info(ydl, url, download=True):
                """
                Wrap yt-dlp extraction in a cancellable task
                
                This function wraps the yt-dlp extract_info method in an asynchronous task
                that can be cancelled. It also handles cache hits by catching the custom
                CachedVideoFound exception and returning the cached information.
                
                Args:
                    ydl (YoutubeDL): The yt-dlp instance to use for extraction
                    url (str): The URL to extract information from
                    download (bool, optional): Whether to download the media. Defaults to True.
                    
                Returns:
                    dict: Information about the extracted media, including file path and metadata
                    
                Raises:
                    Various exceptions from yt-dlp that are caught by the caller
                """
                try:
                    self.current_ydl = ydl
                    loop = asyncio.get_event_loop()
                    try:
                        info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=download))
                        return info
                    except CachedVideoFound as e:  # Using our custom exception from logging module
                        # Video was found in cache, return the cached info
                        cached_path = e.cached_info['file_path']
                        video_id = e.cached_info.get('id')
                        
                        # Verify the file exists
                        if not os.path.exists(cached_path):
                            print(f"{RED}Cached file not found: {cached_path}{RESET}")
                            return None
                            
                        # Use the cached path directly
                        file_path = cached_path
                        
                        # Construct proper YouTube URL
                        youtube_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else url
                            
                        return {
                            'id': video_id,
                            'title': e.cached_info.get('title', 'Unknown'),
                            'url': youtube_url,
                            'webpage_url': youtube_url,
                            'file_path': file_path,
                            'thumbnail': e.cached_info.get('thumbnail'),
                            'is_from_cache': True,
                            'duration': e.cached_info.get('duration', 0),
                            'ext': os.path.splitext(file_path)[1][1:]  # Get extension without dot
                        }
                finally:
                    self.current_ydl = None

            try:
                # Initialize default options
                ydl_opts = {**BASE_YTDL_OPTIONS}
                
                # Add cookies if available
                if os.path.exists(COOKIES_PATH):
                    ydl_opts['cookiefile'] = COOKIES_PATH
                
                # If this is a playlist entry, skip all initial checks and just download
                if skip_url_check and ('youtube.com/watch' in query or 'youtu.be/' in query):
                    ydl_opts.update({
                        'extract_flat': False,
                        'quiet': True,
                        'outtmpl': os.path.join(self.downloads_dir, '%(id)s.%(ext)s')
                    })
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(query, download=True))
                        if not info:
                            raise Exception("Could not extract video information")
                        file_path = os.path.join(self.downloads_dir, f"{info['id']}.{info.get('ext', 'opus')}")
                        
                        # Add to cache
                        if os.path.exists(file_path) and info.get('id'):
                            video_id = info['id']
                            if not playlist_cache.is_video_cached(video_id):
                                playlist_cache.add_to_cache(
                                    video_id, 
                                    file_path,
                                    thumbnail_url=info.get('thumbnail'),
                                    title=info.get('title', 'Unknown')
                                )
                                print(f"{GREEN}Added Youtube file to cache: {RESET}{BLUE}{video_id} - {info.get('title', 'Unknown')}{RESET}")
                        
                        # Get and cache the duration
                        duration = await get_audio_duration(file_path)
                        if duration > 0:
                            self.duration_cache[file_path] = duration

                        return {
                            'title': info['title'],
                            'url': info['webpage_url'] if info.get('webpage_url') else info['url'],
                            'file_path': file_path,
                            'thumbnail': info.get('thumbnail'),
                            'is_stream': False,
                            'is_from_playlist': True,
                            'ctx': status_msg.channel if status_msg else None,
                            'is_from_cache': True
                        }

                # If not in cache or not a YouTube video, proceed with normal download
                is_youtube_mix = False
                
                # Check if the input is a URL
                if is_url(query):
                    # Convert YouTube watch URL to live URL if it's a livestream
                    if 'youtube.com/watch' in query:
                        video_id = query.split('watch?v=')[1].split('&')[0]
                        # First check if it's a livestream without downloading
                        with yt_dlp.YoutubeDL({
                            **ydl_opts,
                            'extract_flat': True,
                            'quiet': True
                        }) as ydl:
                            try:
                                info = ydl.extract_info(query, download=False)
                                is_live = info.get('is_live', False) or info.get('live_status') in ['is_live', 'post_live', 'is_upcoming']
                                if is_live:
                                    query = f"https://www.youtube.com/live/{video_id}"
                            except Exception as e:
                                print(f"Error checking livestream status: {e}")
                                # Don't assume it's not live if we can't check, continue with normal download
                                is_live = False
                    # Handle YouTube Mix playlists
                    is_youtube_mix = 'start_radio=1' in query or 'list=RD' in query
                    if is_youtube_mix:
                        ydl_opts['playlistend'] = config_vars.get('MIX_PLAYLIST_LIMIT', 50)
                else:
                    # If it's not a URL, treat it as a search term
                    original_query = query
                    query = f"ytsearch1:{query}"  # Only get the first result
                    ydl_opts['noplaylist'] = True  # Never process playlists for search queries
                    
                    # First, do a quick check to see if the search returns a channel
                    with yt_dlp.YoutubeDL({
                        'quiet': True,
                        'extract_flat': True,
                        'force_generic_extractor': False,
                        'ignoreerrors': True
                    }) as ydl:
                        try:
                            search_results = ydl.extract_info(query, download=False)
                            
                            # Check if the result is a channel
                            if search_results and search_results.get('_type') == 'playlist' and search_results.get('entries'):
                                first_entry = search_results['entries'][0] if search_results['entries'] else None
                                if first_entry and first_entry.get('url') and '/channel/' in first_entry.get('url', ''):
                                    channel_url = first_entry.get('url')
                                    
                                    # Extract channel ID
                                    channel_id = None
                                    if '/channel/UC' in channel_url:
                                        channel_id = channel_url.split('/channel/UC')[1].split('/')[0]
                                        if channel_id:
                                            # Convert to playlist URL
                                            playlist_url = f"https://www.youtube.com/playlist?list=UU{channel_id}"
                                            
                                            if status_msg:
                                                await status_msg.edit(embed=create_embed(
                                                    "Channel Detected",
                                                    f"Found channel for {original_query}. Processing as a playlist...",
                                                    color=0x3498db,
                                                    ctx=ctx
                                                ))
                                            
                                            # Handle as a playlist
                                            await self._handle_playlist(playlist_url, ctx, status_msg)
                                            return None
                        except Exception as e:
                            # Continue with normal download if check fails
                            pass

                # Skip pre-check for direct YouTube watch URLs (no playlist/mix)
                is_direct_watch = ('youtube.com/watch' in query or 'youtu.be/' in query) and not is_youtube_mix
                
                if not is_direct_watch and is_url(query):
                    # First, extract info without downloading to check if it's a livestream or mix
                    with yt_dlp.YoutubeDL({
                        **ydl_opts, 
                        'extract_flat': True,
                        'noplaylist': not is_youtube_mix  # Allow playlist only for Mix URLs
                    }) as ydl:
                        self.current_download_task = asyncio.create_task(extract_info(ydl, query, download=False))
                        try:
                            info_dict = await self.current_download_task
                            
                            # Check if the result is a channel
                            if info_dict and info_dict.get('_type') == 'playlist' and info_dict.get('entries'):
                                # Check if the first result is a channel
                                if info_dict['entries'] and info_dict['entries'][0]:
                                    first_entry = info_dict['entries'][0]
                                    if first_entry.get('url') and '/channel/' in first_entry.get('url', ''):
                                        channel_url = first_entry.get('url')
                                        
                                        # Extract channel ID
                                        channel_id = None
                                        if '/channel/UC' in channel_url:
                                            channel_id = channel_url.split('/channel/UC')[1].split('/')[0]
                                            if channel_id:
                                                # Convert to playlist URL
                                                playlist_url = f"https://www.youtube.com/playlist?list=UU{channel_id}"
                                                
                                                if status_msg:
                                                    await status_msg.edit(embed=create_embed(
                                                        "Channel Detected",
                                                        f"Found channel for {query}. Processing as a playlist...",
                                                        color=0x3498db,
                                                        ctx=ctx
                                                    ))
                                                
                                                # Handle as a playlist
                                                await self._handle_playlist(playlist_url, ctx, status_msg)
                                                return None
                            
                            # Enhanced livestream detection
                            is_live = (
                                info_dict.get('is_live', False) or 
                                info_dict.get('live_status') in ['is_live', 'post_live', 'is_upcoming']
                            )

                            if is_live:
                                # Extract the direct stream URL from formats list
                                direct_stream_url = None
                                formats = info_dict.get('formats', [])
                                
                                # First try to find an audio-only format for efficiency
                                for format in formats:
                                    if format.get('acodec') != 'none' and format.get('vcodec') == 'none':
                                        direct_stream_url = format.get('url')
                                        break
                                
                                # If no audio-only format, use the best available format
                                if not direct_stream_url and formats:
                                    # Try to find a format with both audio and video
                                    for format in formats:
                                        if format.get('acodec') != 'none':
                                            direct_stream_url = format.get('url')
                                            break
                                
                                # Last resort: use the general URL or the query itself
                                if not direct_stream_url:
                                    direct_stream_url = info_dict.get('url', query)
                                                                
                                # Clean up the title by removing date, time and (live) suffix if present
                                title = info_dict.get('title', 'Livestream')
                                if title.endswith(datetime.now().strftime("%Y-%m-%d %H:%M")):
                                    title = title.rsplit(' ', 2)[0]  # Remove the date and time
                                if title.endswith('(live)'):
                                    title = title[:-6].strip()  # Remove (live) suffix
                                result = {
                                    'title': title,
                                    'url': query,  # Keep the YouTube URL for display
                                    'file_path': direct_stream_url,  # Use the direct stream URL for playback
                                    'is_stream': True,
                                    'is_live': True,
                                    'thumbnail': info_dict.get('thumbnail'),
                                    'duration': None
                                }
                                if status_msg:
                                    await status_msg.delete()
                                return result

                            # Handle YouTube Mix playlist
                            if is_youtube_mix and info_dict.get('_type') == 'playlist':
                                print(f"YouTube Mix playlist detected: {query}")
                                entries = info_dict.get('entries', [])
                                if entries:
                                    total_videos = len(entries)
                                    playlist_title = info_dict.get('title', 'YouTube Mix')
                                    playlist_url = info_dict.get('webpage_url', query)
                                    
                                    if status_msg:
                                        description = f"[{playlist_title}]({playlist_url})\nEntries: {total_videos}\n\nThis might take a while..."
                                        playlist_embed = create_embed(
                                            "Processing YouTube Mix",
                                            description,
                                            color=0x3498db,
                                            ctx=progress.ctx
                                        )
                                        # Get thumbnail from first entry
                                        if entries and entries[0]:
                                            first_entry = entries[0]
                                            thumbnail_url = first_entry.get('thumbnails', [{}])[0].get('url') if first_entry.get('thumbnails') else None
                                            if not thumbnail_url:
                                                thumbnail_url = first_entry.get('thumbnail')
                                            if thumbnail_url:
                                                playlist_embed.set_thumbnail(url=thumbnail_url)
                                        await status_msg.edit(embed=playlist_embed)
                                        await status_msg.delete(delay=10)

                                    # Process the first song immediately
                                    first_entry = entries[0]
                                    first_video_url = f"https://youtube.com/watch?v={first_entry['id']}"
                                    first_song = await self.download_song(first_video_url, status_msg=None)
                                    
                                    if first_song:
                                        first_song['is_from_playlist'] = True
                                        # Process remaining songs in the background
                                        async def process_remaining_songs():
                                            """
                                            Process the remaining songs in a playlist in the background
                                            
                                            This function is called after the first song of a playlist has been
                                            processed and added to the queue. It downloads and processes the
                                            remaining songs in the playlist asynchronously, adding them to the
                                            queue as they become available.
                                            
                                            The function:
                                            1. Iterates through the remaining entries in the playlist
                                            2. Downloads each song using the download_song method
                                            3. Marks each song as being from a playlist
                                            4. Adds each song to the queue
                                            5. Starts playback if needed
                                            
                                            Any errors during processing are caught and logged to prevent
                                            the entire playlist from failing if one song has an issue.
                                            """
                                            try:
                                                for entry in entries[1:]:
                                                    if entry:
                                                        video_url = f"https://youtube.com/watch?v={entry['id']}"
                                                        song_info = await self.download_song(video_url, status_msg=None)
                                                        if song_info:
                                                            song_info['is_from_playlist'] = True
                                                            async with self.queue_lock:
                                                                self.queue.append(song_info)
                                                                if not self.is_playing and not self.voice_client.is_playing() and len(self.queue) == 1:
                                                                    await play_next(progress.ctx)
                                            except Exception as e:
                                                print(f"Error processing Mix playlist: {str(e)}")
                                        
                                        # Start background processing
                                        asyncio.create_task(process_remaining_songs())
                                        return first_song
                                raise Exception("No songs found in the Mix playlist")

                        except asyncio.CancelledError:
                            print("Info extraction cancelled")
                            await progress.cleanup()
                            raise Exception("Download cancelled")
                        except Exception as e:
                            print(f"Error checking livestream status: {e}")
                            is_live = False
                else:
                    # For search terms, just proceed with the download directly
                    pass
                
                # For non-livestream content, proceed with normal download
                ydl_opts = {
                    **BASE_YTDL_OPTIONS,
                    'outtmpl': os.path.join(self.downloads_dir, '%(id)s.%(ext)s'),
                    'cookiefile': COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
                    'progress_hooks': [
                        self._download_hook,
                        progress.progress_hook
                    ],
                    'default_search': 'ytsearch'
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    self.current_download_task = asyncio.create_task(extract_info(ydl, query, download=True))
                    try:
                        info = await self.current_download_task
                    except asyncio.CancelledError:
                        print("Download cancelled")
                        await progress.cleanup()
                        raise Exception("Download cancelled")
                    
                    # Clean up the progress tracker after successful download
                    await progress.cleanup()
                    
                    # Check if the result is a YouTube channel
                    if info and info.get('_type') == 'playlist' and info.get('entries'):
                        # Check if this is a channel result (many entries with same uploader)
                        if len(info.get('entries', [])) > 10:
                            # Check if all entries have the same uploader
                            uploaders = set()
                            for entry in info.get('entries', [])[:10]:
                                if entry and entry.get('uploader'):
                                    uploaders.add(entry.get('uploader'))
                            
                            if len(uploaders) == 1:
                                uploader = next(iter(uploaders))
                                
                                # Convert channel URL to playlist URL as recommended in the logs
                                if info.get('id') and info.get('id').startswith('UC'):
                                    channel_id = info.get('id')
                                    playlist_url = f"https://www.youtube.com/playlist?list=UU{channel_id[2:]}"
                                    
                                    if status_msg:
                                        await status_msg.edit(embed=create_embed(
                                            "Channel Detected",
                                            f"Found channel for {uploader}. Processing as a playlist...",
                                            color=0x3498db,
                                            ctx=ctx
                                        ))
                                    
                                    # Handle as a playlist
                                    await self._handle_playlist(playlist_url, ctx, status_msg)
                                    return None
                    
                    if info.get('_type') == 'playlist' and not is_playlist_url(query):
                        # Handle search results that return a playlist
                        if not info.get('entries'):
                            raise Exception("No results found for your search.\nPlease try again with another search term")
                        # Make sure we have a valid entry
                        if len(info['entries']) > 0 and info['entries'][0]:
                            info = info['entries'][0]
                            file_path = os.path.join(self.downloads_dir, f"{info['id']}.{info.get('ext', 'opus')}")
                        else:
                            raise Exception("No valid results found for your search")
                    
                    elif info.get('_type') == 'playlist' and is_playlist_url(query):
                        # Handle actual playlist URLs
                        if not info.get('entries'):
                            raise Exception("Playlist is empty")

                        ctx = (ctx or status_msg.channel) if status_msg else None
                        
                        # Check if entries list is not empty before accessing
                        if not info['entries']:
                            raise Exception("No videos found in the playlist")
                            
                        first_video = info['entries'][0]
                        if not first_video:
                            raise Exception("First video in playlist is invalid")
                            
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
                    
                    # Add to cache for both YouTube direct links and Spotify->YouTube conversions
                    if os.path.exists(file_path) and info.get('id'):
                        video_id = info['id']
                        if not playlist_cache.is_video_cached(video_id):
                            playlist_cache.add_to_cache(
                                video_id, 
                                file_path,
                                thumbnail_url=info.get('thumbnail'),
                                title=info.get('title', 'Unknown')  # Save the title
                            )
                            print(f"{GREEN}Added Youtube file to cache: {RESET}{BLUE}{video_id} - {info.get('title', 'Unknown')}{RESET}")

                    # Add requester information to the song info
                    if ctx:
                        info['requester'] = ctx.author
                    
                    # Get and cache the duration
                    duration = await get_audio_duration(file_path)
                    if duration > 0:
                        self.duration_cache[file_path] = duration

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
                error_msg = str(e)
                
                # Check for video unavailable message and add to blacklist
                if ('Video unavailable' in error_msg and 'youtube' in query.lower()) or 'No video formats found' in error_msg:
                    video_id = None
                    try:
                        if 'youtube.com/watch' in query:
                            video_id = query.split('watch?v=')[1].split('&')[0] if 'watch?v=' in query else None
                        elif 'youtu.be/' in query:
                            video_id = query.split('youtu.be/')[1].split('?')[0] if 'youtu.be/' in query else None
                    except Exception as e:
                        print(f"Error extracting video ID for blacklisting: {e}")
                        
                    if video_id:
                        print(f"{RED}Video ID {video_id} is unavailable, blacklisting...{RESET}")
                        playlist_cache.add_to_blacklist(video_id)
                        
                if status_msg:
                    error_embed = create_embed(
                        "Error ❌",
                        str(e),
                        color=0xe74c3c,
                        ctx=ctx if ctx else status_msg.channel
                    )
                    await status_msg.edit(embed=error_embed)
                await progress.cleanup()
                raise

        except Exception as e:
            print(f"Error downloading song: {str(e)}")
            if status_msg:
                error_embed = create_embed(
                    "Error ❌",
                    str(e),
                    color=0xe74c3c,
                    ctx=ctx if ctx else status_msg.channel
                )
                await status_msg.edit(embed=error_embed)
            await progress.cleanup()
            raise

    async def update_activity(self):
        """
        Update the bot's activity status
        
        This method delegates to the update_activity function in the activity module
        to update the bot's Discord presence based on the current playback state.
        It passes the current song information and playing status to display
        appropriate information in the bot's status.
        
        The bot's status will show:
        - The currently playing song title when a song is playing
        - A default message prompting users to use the play command when idle
        
        This helps users quickly see what the bot is currently doing.
        """
        if self.bot:
            await update_activity(self.bot, self.current_song, self.is_playing)

    def show_credentials(self):
        """
        Display credential status for Spotify, YouTube, and Genius
        This method can be called explicitly when needed
        """
        # Load Spotify API credentials from environment file
        load_dotenv(dotenv_path=".spotifyenv")
        client_id = os.getenv('SPOTIPY_CLIENT_ID')
        client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        
        # Check if Spotify credentials are available
        print(f"{GREEN}Spotify credentials found:{RESET} {BLUE if (client_id and client_secret) else RED}{'Yes' if (client_id and client_secret) else 'No'}{RESET}")
        
        # Check for YouTube cookies file (needed for age-restricted content)
        if os.path.exists(COOKIES_PATH):
            print(f"{GREEN}YouTube cookies found:{RESET} {BLUE}Yes{RESET}")
        else:
            print(f"{GREEN}YouTube cookies found:{RESET} {RED}No{RESET}")
            print(f"{RED}Warning: YouTube cookies not found, YouTube functionality might be limited.{RESET}")
            print(f'{BLUE}Extract using "Get Cookies" extension and save it as cookies.txt in the root directory where you run the bot.{RESET}')
            print(f"{BLUE}https://github.com/yt-dlp/yt-dlp/wiki/How-to-use-cookies{RESET}\n")
            
        # Check for Genius lyrics API token
        genius_token_file = Path(__file__).parent.parent / '.geniuslyrics'
        if genius_token_file.exists():
            with open(genius_token_file, 'r') as f:
                content = f.read().strip()
                has_token = content and not content.endswith('=')
            print(f"{GREEN}Genius lyrics token found:{RESET} {BLUE if has_token else RED}{'Yes' if has_token else 'No'}{RESET}")
            if not has_token:
                print(f"{RED}Warning: Genius lyrics token not found.\n{BLUE}AZLyrics will be used as a fallback.{RESET}")
                print(f"{BLUE}https://genius.com/api-clients{RESET}")
                print(f'{BLUE}Update your {RESET}{YELLOW}.geniuslyrics file{RESET}')
                print(f"{BLUE}Format: client_access_token=your_token_here{RESET}")
            print(f"----------------------------------------")

    def __del__(self):
        """Destructor to clean up resources when the bot instance is deleted"""
        try:
            # Clean up any resources that need explicit closing
            pass
        except Exception as e:
            print(f"Error during MusicBot cleanup: {str(e)}")