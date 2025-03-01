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
    # Check if music_bot is None, if so, return immediately
    if not music_bot:
        return
        
    # Check if the bot is already handling a song or if the queue is empty
    # If either condition is true, return immediately
    if music_bot.waiting_for_song or not music_bot.queue:
        return

    # Set the flag to prevent multiple simultaneous playbacks
    music_bot.waiting_for_song = True
    music_bot.is_playing = False  # Reset playing state

    try:
        # Get the next song from the queue
        song = music_bot.queue.pop(0)
        
        # Get the context for the song
        song_ctx = song.get('ctx')
        if not song_ctx:
            # If context is missing, use the provided ctx or the last known context
            if ctx:
                song_ctx = ctx
            else:
                # If context is missing, print a warning and use the last known context
                print("Warning: Missing context in song, using last known context")
                if hasattr(music_bot, 'last_known_ctx'):
                    song_ctx = music_bot.last_known_ctx
                else:
                    # If no context is available, print an error and return
                    print("Error: No context available for playback")
                    music_bot.waiting_for_song = False
                    if music_bot.queue:
                        # Try to play the next song in the queue
                        await process_queue(music_bot, ctx)
                    return

        # Update the last known context
        music_bot.last_known_ctx = song_ctx

        # Check if the bot is connected to a voice channel
        if not music_bot.voice_client or not music_bot.voice_client.is_connected():
            try:
                # Try to join the voice channel
                if hasattr(music_bot, 'join_voice_channel'):
                    connected = await music_bot.join_voice_channel(song_ctx)
                    if not connected:
                        # If connection fails, print an error and return
                        print("Failed to connect to voice channel")
                        music_bot.waiting_for_song = False
                        return
            except Exception as e:
                # If an error occurs while connecting, print the error and return
                print(f"Error connecting to voice channel: {str(e)}")
                music_bot.waiting_for_song = False
                return

        # Set the current song
        music_bot.current_song = song
        music_bot.is_playing = True
        music_bot.last_activity = time.time()

        # Clean up the queued message for the song that's about to play
        if song['url'] in music_bot.queued_messages:
            try:
                # Delete the queued message
                await music_bot.queued_messages[song['url']].delete()
                del music_bot.queued_messages[song['url']]
            except Exception as e:
                # If an error occurs while deleting the message, print the error
                print(f"Error deleting queued message: {str(e)}")

        # Check if the file exists for non-stream content
        if not song.get('is_stream') and not Path(song['file_path']).exists():
            # If the file does not exist, print an error and try to play the next song
            print(f"Error: File not found: {song['file_path']}")
            music_bot.waiting_for_song = False
            music_bot.is_playing = False
            
            if music_bot.queue:
                await process_queue(music_bot, ctx)
            return

        # Use the original requester if available, otherwise use the context
        requester = song.get('requester', song_ctx.author)
        ctx_with_requester = song_ctx
        if requester and requester != song_ctx.author:
            # Create a context-like object with the requester information
            class DummyCtx:
                def __init__(self, author):
                    self.author = author
            ctx_with_requester = DummyCtx(requester)

        # Check if we should send the now playing message
        if should_send_now_playing(music_bot, song['title']):
            # Create the now playing embed
            now_playing_embed = create_embed(
                "Now playing 🎵",
                f"[{song['title']}]({song['url']})",
                color=0x00ff00,
                thumbnail_url=song.get('thumbnail'),
                ctx=ctx_with_requester
            )
            
            # Create view with buttons if enabled
            view = create_now_playing_view()
            
            kwargs = {'embed': now_playing_embed}
            if view is not None:
                kwargs['view'] = view
                
            # Send the now playing message
            music_bot.now_playing_message = await song_ctx.send(**kwargs)

        # Update bot presence with current song
        try:
            if music_bot.bot:
                # Use the update_activity function to respect the SHOW_ACTIVITY_STATUS setting
                await update_activity(music_bot.bot, song, is_playing=True)
        except Exception as e:
            # If an error occurs while updating presence, print the error
            print(f"Error updating presence: {str(e)}")

        # Reset command tracking
        music_bot.current_command_msg = None
        music_bot.current_command_author = None

        # Play the audio
        try:
            # Check if already playing before attempting to play
            if music_bot.voice_client and music_bot.voice_client.is_playing():
                # If already playing, stop the current playback
                print("Already playing audio, stopping current playback")
                music_bot.voice_client.stop()
                
            if music_bot.voice_client and music_bot.voice_client.is_connected():
                # For streams, we need to use a different approach
                if song.get('is_stream'):
                    # Create an audio source for the stream
                    audio_source = discord.FFmpegPCMAudio(
                        song['file_path'],  # Use file_path which contains the direct stream URL
                        **FFMPEG_OPTIONS
                    )
                else:
                    # Create an audio source for the file
                    audio_source = discord.FFmpegPCMAudio(
                        song['file_path'],
                        **FFMPEG_OPTIONS
                    )
                
                # Call read() on the audio source before playing to prevent speed-up issue
                audio_source.read()
                
                # Set the playback start time right before starting playback
                music_bot.playback_start_time = time.time()
                music_bot.playback_state = "playing"
                
                # Log the now playing message with server name
                server_name = song_ctx.guild.name if song_ctx and hasattr(song_ctx, 'guild') and song_ctx.guild else "Unknown Server"
                print(f"{GREEN}Now playing:{RESET}{BLUE} {song['title']}{RESET}{GREEN} in server: {RESET}{BLUE}{server_name}{RESET}")
                
                # Set volume
                volume_transformer = discord.PCMVolumeTransformer(audio_source, volume=DEFAULT_VOLUME/100.0)
                
                # Play the audio
                music_bot.voice_client.play(
                    volume_transformer,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        music_bot.after_playing_coro(e, song_ctx), 
                        music_bot.bot_loop or asyncio.get_event_loop()
                    )
                )
        except Exception as e:
            # If an error occurs while playing audio, print the error and try to play the next song
            print(f"Error playing audio: {str(e)}")
            music_bot.waiting_for_song = False
            music_bot.is_playing = False
            
            if music_bot.queue:
                await process_queue(music_bot, ctx)
    except Exception as e:
        # If an error occurs in the process_queue function, print the error and try to play the next song
        print(f"Error in process_queue: {str(e)}")
        music_bot.waiting_for_song = False
        music_bot.is_playing = False
        
        if music_bot.queue:
            await process_queue(music_bot, ctx)
    finally:
        # Reset the waiting flag regardless of success or failure
        music_bot.waiting_for_song = False