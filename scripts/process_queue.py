import discord
import asyncio
import time
from pathlib import Path
from scripts.activity import update_activity
from scripts.duration import get_audio_duration
from scripts.messages import create_embed, should_send_now_playing
from scripts.config import FFMPEG_OPTIONS, load_config
from scripts.ui_components import create_now_playing_view
from scripts.constants import RED, GREEN, BLUE, RESET
from scripts.playback import (
    cleanup_queued_message,
    verify_audio_file,
    get_requester_context,
    send_now_playing_message,
    update_bot_presence,
    start_playback,
    is_bot_explicitly_stopped,
)

# Get default volume from config
config = load_config()
DEFAULT_VOLUME = config.get('DEFAULT_VOLUME', 100)

async def process_queue(music_bot, ctx=None):
    """
    Process the song queue.
    
    This function handles the initial playback of a song from the queue.
    It manages connecting to voice channels, setting up the current song,
    creating the now playing message, and starting audio playback.
    
    The function includes error handling to ensure that if one song fails to play,
    the bot will attempt to play the next song in the queue. It also manages
    the bot's presence to show the currently playing song.
    
    Args:
        music_bot: The music bot instance containing the queue and voice client
        ctx: Optional context to use if the song's context is missing
    """
    # Check if music_bot is None
    if not music_bot:
        return
        
    # Check if the bot is already handling a song or if the queue is empty
    if music_bot.waiting_for_song or not music_bot.queue:
        return
        
    # Check if the bot has been explicitly stopped
    if is_bot_explicitly_stopped(music_bot):
        async with music_bot.queue_lock:
            music_bot.queue.clear()
        return

    # Set the flag to prevent multiple simultaneous playbacks
    music_bot.waiting_for_song = True
    music_bot.is_playing = False

    try:
        # Get the next song from the queue
        async with music_bot.queue_lock:
            song = music_bot.queue.popleft()
        
        # Get the context for the song
        song_ctx = song.get('ctx') or ctx
        if not song_ctx:
            print("Warning: Missing context in song, using last known context")
            song_ctx = getattr(music_bot, 'last_known_ctx', None)
            if not song_ctx:
                print("Error: No context available for playback")
                music_bot.waiting_for_song = False
                if music_bot.queue:
                    await process_queue(music_bot, ctx)
                return

        # Update the last known context
        music_bot.last_known_ctx = song_ctx

        # Check if the bot is connected to a voice channel
        if not music_bot.voice_client or not music_bot.voice_client.is_connected():
            try:
                if hasattr(music_bot, 'join_voice_channel'):
                    connected = await music_bot.join_voice_channel(song_ctx)
                    if not connected:
                        print("Failed to connect to voice channel")
                        music_bot.waiting_for_song = False
                        return
            except Exception as e:
                print(f"Error connecting to voice channel: {str(e)}")
                music_bot.waiting_for_song = False
                return

        # Set the current song
        music_bot.current_song = song
        music_bot.is_playing = True
        music_bot.last_activity = time.time()

        # Clean up the queued message
        await cleanup_queued_message(music_bot, song['url'])

        # Check if the file exists for non-stream content
        if not verify_audio_file(song['file_path'], song.get('is_stream', False)):
            print(f"Error: File not found: {song['file_path']}")
            music_bot.waiting_for_song = False
            music_bot.is_playing = False
            if music_bot.queue:
                await process_queue(music_bot, ctx)
            return

        # Send now playing message
        await send_now_playing_message(music_bot, song, song_ctx)

        # Update bot presence
        await update_bot_presence(music_bot, song, is_playing=True)

        # Reset command tracking
        music_bot.current_command_msg = None
        music_bot.current_command_author = None

        # Start playback
        success = await start_playback(
            music_bot, 
            song, 
            song_ctx,
            use_volume_transformer=True
        )
        
        if not success:
            music_bot.waiting_for_song = False
            music_bot.is_playing = False
            if music_bot.queue:
                await process_queue(music_bot, ctx)

    except Exception as e:
        print(f"Error in process_queue: {str(e)}")
        music_bot.waiting_for_song = False
        music_bot.is_playing = False
        if music_bot.queue:
            await process_queue(music_bot, ctx)
    finally:
        # Reset the waiting flag regardless of success or failure
        music_bot.waiting_for_song = False