import discord
import asyncio
import time
from pathlib import Path
from scripts.duration import get_audio_duration
from scripts.messages import create_embed, should_send_now_playing
from scripts.config import FFMPEG_OPTIONS, load_config
from scripts.ui_components import create_now_playing_view
from scripts.constants import RED, GREEN, BLUE, RESET

# Get default volume from config
config = load_config()
DEFAULT_VOLUME = config.get('DEFAULT_VOLUME', 100)

async def process_queue(music_bot):
    """Process the song queue"""
    if not music_bot:
        return
        
    # Don't process if we're already handling a song or queue is empty
    if music_bot.waiting_for_song or not music_bot.queue:
        return

    # Set the flag to prevent multiple simultaneous playbacks
    music_bot.waiting_for_song = True
    music_bot.is_playing = False  # Reset playing state

    try:
        song = music_bot.queue.pop(0)
        
        ctx = song.get('ctx')
        if not ctx:
            print("Warning: Missing context in song, using last known context")
            if hasattr(music_bot, 'last_known_ctx'):
                ctx = music_bot.last_known_ctx
            else:
                print("Error: No context available for playback")
                music_bot.waiting_for_song = False
                if music_bot.queue:
                    await process_queue(music_bot)
                return

        music_bot.last_known_ctx = ctx

        if not music_bot.voice_client or not music_bot.voice_client.is_connected():
            try:
                # Try to join the voice channel
                if hasattr(music_bot, 'join_voice_channel'):
                    connected = await music_bot.join_voice_channel(ctx)
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

        # Clean up the queued message for the song that's about to play
        if song['url'] in music_bot.queued_messages:
            try:
                await music_bot.queued_messages[song['url']].delete()
                del music_bot.queued_messages[song['url']]
            except Exception as e:
                print(f"Error deleting queued message: {str(e)}")

        # Check if file exists for non-stream content
        if not song.get('is_stream') and not Path(song['file_path']).exists():
            print(f"Error: File not found: {song['file_path']}")
            music_bot.waiting_for_song = False
            music_bot.is_playing = False
            
            # Try the next song
            if music_bot.queue:
                await process_queue(music_bot)
            return

        # Use the original requester if available, otherwise use the context
        requester = song.get('requester', ctx.author)
        ctx_with_requester = ctx
        if requester and requester != ctx.author:
            # Create a context-like object with the requester information
            class DummyCtx:
                def __init__(self, author):
                    self.author = author
            ctx_with_requester = DummyCtx(requester)

        # Check if we should send the now playing message
        if should_send_now_playing(music_bot, song['title']):
            now_playing_embed = create_embed(
                "Now playing ",
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
                
            music_bot.now_playing_message = await ctx.send(**kwargs)

        # Update bot presence with current song
        try:
            if music_bot.bot:
                await music_bot.bot.change_presence(activity=discord.Game(name=f"{song['title']}"))
        except Exception as e:
            print(f"Error updating presence: {str(e)}")

        # Reset command tracking
        music_bot.current_command_msg = None
        music_bot.current_command_author = None

        # Play the audio
        try:
            # Check if already playing before attempting to play
            if music_bot.voice_client and music_bot.voice_client.is_playing():
                print("Already playing audio, stopping current playback")
                music_bot.voice_client.stop()
                
            if music_bot.voice_client and music_bot.voice_client.is_connected():
                # For streams, we need to use a different approach
                if song.get('is_stream'):
                    audio_source = discord.FFmpegPCMAudio(
                        song['url'],
                        **FFMPEG_OPTIONS
                    )
                else:
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
                server_name = ctx.guild.name if ctx and hasattr(ctx, 'guild') and ctx.guild else "Unknown Server"
                print(f"{GREEN}Now playing:{RESET}{BLUE} {song['title']}{RESET}{GREEN} in server: {RESET}{BLUE}{server_name}{RESET}")
                
                # Set volume
                volume_transformer = discord.PCMVolumeTransformer(audio_source, volume=DEFAULT_VOLUME/100.0)
                
                music_bot.voice_client.play(
                    volume_transformer,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        music_bot.after_playing_coro(e, ctx), 
                        music_bot.bot_loop
                    )
                )
        except Exception as e:
            print(f"Error playing audio: {str(e)}")
            music_bot.waiting_for_song = False
            music_bot.is_playing = False
            
            # Try the next song
            if music_bot.queue:
                await process_queue(music_bot)
    except Exception as e:
        print(f"Error in process_queue: {str(e)}")
        music_bot.waiting_for_song = False
        music_bot.is_playing = False
        
        # Try the next song
        if music_bot.queue:
            await process_queue(music_bot)
    finally:
        # Reset the waiting flag regardless of success or failure
        music_bot.waiting_for_song = False