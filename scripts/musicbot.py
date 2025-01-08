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
from scripts.constants import RED, GREEN, BLUE, RESET, SHOW_PROGRESS_BAR
from scripts.activity import update_activity
from scripts.after_playing_coro import AfterPlayingHandler
from scripts.cleardownloads import clear_downloads_folder
from scripts.clear_queue import clear_queue
from scripts.config import load_config, YTDL_OPTIONS, FFMPEG_OPTIONS
from scripts.downloadprogress import DownloadProgress
from scripts.duration import get_audio_duration
from scripts.format_size import format_size
from scripts.handle_playlist import PlaylistHandler
from scripts.handle_spotify import SpotifyHandler
from scripts.inactivity import start_inactivity_checker, check_inactivity
from scripts.load_commands import load_commands
from scripts.load_scripts import load_scripts
from scripts.logging import setup_logging, get_ytdlp_logger
from scripts.messages import update_or_send_message, create_embed
from scripts.play_next import play_next
from scripts.process_queue import process_queue
from scripts.restart import restart_bot
from scripts.spotify import get_spotify_album_details, get_spotify_track_details, get_spotify_playlist_details
from scripts.ui_components import NowPlayingView
from scripts.updatescheduler import check_updates, update_checker
from scripts.url_identifier import is_url, is_playlist_url, is_radio_stream
from scripts.voice import join_voice_channel, leave_voice_channel, handle_voice_state_update
from scripts.ytdlp import get_ytdlp_path, ytdlp_version
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.cache_handler import CacheFileHandler

config_vars = load_config()
INACTIVITY_TIMEOUT = config_vars.get('INACTIVITY_TIMEOUT', 60)

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
        self.downloads_dir = Path(__file__).parent.parent / 'downloads'
        self.cookie_file = Path(__file__).parent.parent / 'cookies.txt'
        self.playback_start_time = None  # Track when the current song started playing
        self.in_progress_downloads = {}  # Track downloads in progress
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
        self.cache_dir = Path(__file__).parent.parent / '.cache'
        self.spotify_cache = self.cache_dir / 'spotify'
        
        # Create cache directories if they don't exist
        self.cache_dir.mkdir(exist_ok=True)
        self.spotify_cache.mkdir(exist_ok=True)

        load_dotenv(dotenv_path=".spotifyenv")
        client_id = os.getenv('SPOTIPY_CLIENT_ID')
        client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        
        print(f"{GREEN}Spotify credentials found:{RESET} {BLUE if (client_id and client_secret) else RED}{'Yes' if (client_id and client_secret) else 'No'}{RESET}")
        
        if not client_id or not client_secret:
            print(f"{RED}Warning: Spotify credentials not found. Spotify functionality will be limited.{RESET}")
            self.sp = None
        else:
            try:
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
                print(f"{RED}Error initializing Spotify client: {str(e)}{RESET}")
                self.sp = None

        if self.cookie_file.exists():
            print(f"{GREEN}YouTube cookies file found:{RESET} {BLUE}Yes{RESET}")
        else:
            print(f"{RED}YouTube cookies not found, features might be limited{RESET}")

    async def setup(self, bot_instance):
        """Setup the bot with the event loop"""
        self.bot = bot_instance
        self.bot_loop = asyncio.get_event_loop()
        await self.start_command_processor()
        await start_inactivity_checker(self)
        asyncio.create_task(self.process_download_queue())
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
                        self.in_progress_downloads[query] = None  # Mark as downloading but no info yet
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
                
            # Create DownloadProgress instance with ctx
            progress = DownloadProgress(status_msg, None)
            progress.ctx = ctx or (status_msg.channel if status_msg else None)
                
            ydl_opts = {
                **YTDL_OPTIONS,
                'outtmpl': os.path.join(self.downloads_dir, '%(id)s.%(ext)s'),
                'cookiefile': self.cookie_file if self.cookie_file.exists() else None,
                'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(
                    progress.progress_hook(d), 
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
