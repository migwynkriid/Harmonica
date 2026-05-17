"""
Shared playback utilities for the music bot.

This module contains common functionality used by both play_next.py and
process_queue.py to avoid code duplication. It provides helper classes
and functions for managing audio playback state and UI updates.
"""

import discord
import asyncio
import time
import os
from pathlib import Path
from scripts.messages import create_embed, should_send_now_playing
from scripts.config import FFMPEG_OPTIONS, load_config
from scripts.ui_components import create_now_playing_view
from scripts.activity import update_activity
from scripts.constants import GREEN, BLUE, RESET, EMBED_COLOR_NOW_PLAYING

# Get default volume from config
config = load_config()
DEFAULT_VOLUME = config.get('DEFAULT_VOLUME', 100)


class RequesterContext:
    """
    A minimal context-like object that holds author information.
    
    Used when we need to display requester information in embeds
    but don't have the original command context available.
    """
    def __init__(self, author):
        self.author = author


def create_song_entry(download_result: dict, ctx, is_from_playlist: bool = False) -> dict:
    """
    Create a standardized song entry dictionary for the queue.
    
    This ensures consistent song data structure across all queue additions.
    
    Args:
        download_result: The result from download_song() containing title, url, file_path, etc.
        ctx: The command context (for requester info)
        is_from_playlist: Whether this song is from a playlist
        
    Returns:
        dict: A standardized song entry for the queue
    """
    return {
        'title': download_result['title'],
        'url': download_result['url'],
        'file_path': download_result['file_path'],
        'thumbnail': download_result.get('thumbnail'),
        'ctx': ctx,
        'is_stream': download_result.get('is_stream', False),
        'is_from_playlist': is_from_playlist or download_result.get('is_from_playlist', False),
        'requester': ctx.author
    }


async def cleanup_queued_message(music_bot, song_url: str) -> None:
    """
    Clean up the queued message for a song that's about to play.
    
    Args:
        music_bot: The MusicBot instance
        song_url: The URL of the song to clean up
    """
    async with music_bot.queued_messages_lock:
        if song_url in music_bot.queued_messages:
            try:
                await music_bot.queued_messages[song_url].delete()
                del music_bot.queued_messages[song_url]
            except Exception as e:
                print(f"Error deleting queued message: {str(e)}")


def verify_audio_file(file_path: str, is_stream: bool = False) -> bool:
    """
    Verify that an audio file exists and is ready for playback.
    
    Args:
        file_path: Path to the audio file
        is_stream: Whether this is a stream URL (skips file check)
        
    Returns:
        bool: True if file exists or is a stream, False otherwise
    """
    if is_stream:
        return True
    return os.path.exists(file_path) or Path(file_path).exists()


def get_requester_context(song: dict, fallback_ctx):
    """
    Get a context object with the correct requester information.
    
    Args:
        song: The song dictionary containing optional 'requester' key
        fallback_ctx: Fallback context if no requester in song
        
    Returns:
        Context-like object with author attribute
    """
    requester = song.get('requester')
    if requester and (not hasattr(fallback_ctx, 'author') or requester != fallback_ctx.author):
        return RequesterContext(requester)
    return fallback_ctx


async def send_now_playing_message(music_bot, song: dict, ctx) -> None:
    """
    Send or update the now playing message.
    
    Args:
        music_bot: The MusicBot instance
        song: The song dictionary with title, url, thumbnail
        ctx: The context to send the message in
    """
    if not should_send_now_playing(music_bot, song['title']):
        return
        
    ctx_with_requester = get_requester_context(song, ctx)
    
    now_playing_embed = create_embed(
        "Now playing 🎵",
        f"[{song['title']}]({song['url']})",
        color=EMBED_COLOR_NOW_PLAYING,
        thumbnail_url=song.get('thumbnail'),
        ctx=ctx_with_requester
    )
    
    view = create_now_playing_view()
    kwargs = {'embed': now_playing_embed}
    if view is not None:
        kwargs['view'] = view
        
    music_bot.now_playing_message = await ctx.send(**kwargs)


async def update_bot_presence(music_bot, song: dict, is_playing: bool = True) -> None:
    """
    Update the bot's Discord presence with current song info.
    
    Args:
        music_bot: The MusicBot instance
        song: The song dictionary (can be None when stopping)
        is_playing: Whether music is currently playing
    """
    try:
        if music_bot.bot:
            await update_activity(music_bot.bot, song, is_playing=is_playing)
    except Exception as e:
        print(f"Error updating presence: {str(e)}")


def create_audio_source(file_path: str, use_volume_transformer: bool = True):
    """
    Create an audio source for playback.
    
    Args:
        file_path: Path to the audio file or stream URL
        use_volume_transformer: Whether to wrap with PCMVolumeTransformer
        
    Returns:
        The audio source ready for playback
    """
    audio_source = discord.FFmpegPCMAudio(file_path, **FFMPEG_OPTIONS)
    # Call read() to prevent speed-up issue
    audio_source.read()
    
    if use_volume_transformer:
        return discord.PCMVolumeTransformer(audio_source, volume=DEFAULT_VOLUME / 100.0)
    return audio_source


def create_after_callback(music_bot, ctx):
    """
    Create a safe after-playback callback.
    
    Args:
        music_bot: The MusicBot instance
        ctx: The context for the callback
        
    Returns:
        A callback function for voice_client.play()
    """
    def callback(error):
        try:
            loop = music_bot.bot_loop or asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                music_bot.after_playing_coro(error, ctx),
                loop
            )
        except Exception as e:
            print(f"Error in after_playing callback: {str(e)}")
    return callback


def log_now_playing(song_title: str, server_name: str = "Unknown Server") -> None:
    """
    Log the currently playing song to console.
    
    Args:
        song_title: Title of the song
        server_name: Name of the server
    """
    print(f"{GREEN}Now playing:{RESET}{BLUE} {song_title}{RESET}{GREEN} in server: {RESET}{BLUE}{server_name}{RESET}")


async def start_playback(music_bot, song: dict, ctx, use_volume_transformer: bool = True) -> bool:
    """
    Start audio playback for a song.
    
    This is the core playback function that handles all the common setup
    needed to start playing audio.
    
    Args:
        music_bot: The MusicBot instance
        song: The song dictionary with file_path, title, etc.
        ctx: The context for sending messages
        use_volume_transformer: Whether to use volume control
        
    Returns:
        bool: True if playback started successfully, False otherwise
    """
    # Verify voice client is connected
    if not music_bot.voice_client or not music_bot.voice_client.is_connected():
        print("Voice client not connected for playback")
        return False
    
    # Stop any current playback
    if music_bot.voice_client.is_playing():
        print("Already playing audio, stopping current playback")
        music_bot.voice_client.stop()
    
    try:
        # Create audio source
        audio_source = create_audio_source(
            song['file_path'],
            use_volume_transformer=use_volume_transformer
        )
        
        # Set playback state
        music_bot.playback_start_time = time.time()
        music_bot.playback_state = "playing"
        
        # Log to console
        server_name = "Unknown Server"
        if ctx and hasattr(ctx, 'guild') and ctx.guild:
            server_name = ctx.guild.name
        log_now_playing(song['title'], server_name)
        
        # Create callback and start playback
        after_callback = create_after_callback(music_bot, ctx)
        music_bot.voice_client.play(audio_source, after=after_callback)
        
        return True
        
    except Exception as e:
        print(f"Error starting playback: {str(e)}")
        return False


def is_bot_explicitly_stopped(music_bot) -> bool:
    """
    Check if the bot has been explicitly stopped.
    
    Args:
        music_bot: The MusicBot instance
        
    Returns:
        bool: True if explicitly stopped, False otherwise
    """
    return hasattr(music_bot, 'explicitly_stopped') and music_bot.explicitly_stopped


def is_voice_connected(music_bot) -> bool:
    """
    Check if the music bot's voice client is connected.
    
    This is the canonical way to check voice connection status.
    
    Args:
        music_bot: The MusicBot instance
        
    Returns:
        bool: True if voice client exists and is connected
    """
    return music_bot.voice_client and music_bot.voice_client.is_connected()


def should_start_playback(music_bot) -> bool:
    """
    Check if playback should start (not already playing or waiting).
    
    Use this to determine if process_queue should be called.
    Checks:
    - music_bot.is_playing flag
    - music_bot.waiting_for_song flag
    - voice_client.is_playing() state
    
    Args:
        music_bot: The MusicBot instance
        
    Returns:
        bool: True if not currently playing and should start
    """
    if not music_bot:
        return False
    if music_bot.is_playing:
        return False
    if getattr(music_bot, 'waiting_for_song', False):
        return False
    if music_bot.voice_client and music_bot.voice_client.is_playing():
        return False
    return True


def is_song_looping(bot, song_url: str) -> bool:
    """
    Check if a song is currently being looped.
    
    Args:
        bot: The Discord bot instance (ctx.bot)
        song_url: URL of the song to check
        
    Returns:
        bool: True if the song is in the loop list
    """
    if not bot:
        return False
    loop_cog = bot.get_cog('Loop') if hasattr(bot, 'get_cog') else None
    if not loop_cog:
        return False
    return song_url in loop_cog.looped_songs
