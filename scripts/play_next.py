import discord
from discord.ui import Button, View
import asyncio
import os
import time
from scripts.messages import create_embed, should_send_now_playing
from scripts.config import load_config, FFMPEG_OPTIONS
from scripts.ui_components import create_now_playing_view
from scripts.constants import RED, GREEN, BLUE, RESET
from scripts.process_queue import process_queue
from scripts.activity import update_activity

# Get default volume from config
config = load_config()
DEFAULT_VOLUME = config.get('DEFAULT_VOLUME', 100)  # Default to 100% if not specified

async def play_next(ctx):
    """
    Play the next song in the queue.
    
    This is the main function that handles playing songs from the queue.
    It manages the transition between songs, updates the now playing message,
    and handles any errors that occur during playback.
    
    The function performs several key tasks:
    1. Gets the next song from the queue
    2. Verifies the audio file exists and is ready to play
    3. Ensures the voice client is connected
    4. Updates the now playing message
    5. Starts playback with the appropriate FFmpeg options
    6. Sets up the after callback to handle song completion
    
    Args:
        ctx: The Discord command context containing guild and channel information
    """
    from bot import MusicBot
    
    # Get server-specific music bot instance
    server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
    
    # Add playback lock to prevent race conditions
    if hasattr(server_music_bot, 'playback_lock'):
        playback_lock = server_music_bot.playback_lock
    else:
        playback_lock = asyncio.Lock()
        server_music_bot.playback_lock = playback_lock
    
    async with playback_lock:
        if len(server_music_bot.queue) > 0:
            try:
                # Store the previous song for reference
                previous_song = server_music_bot.current_song
                # Get the next song from the queue
                server_music_bot.current_song = server_music_bot.queue.pop(0)
                # Update last activity time to prevent inactivity timeout
                server_music_bot.last_activity = time.time()
                server_name = ctx.guild.name if ctx and hasattr(ctx, 'guild') and ctx.guild else "Unknown Server"
                print(f"{GREEN}Now playing:{RESET}{BLUE} {server_music_bot.current_song['title']}{RESET}{GREEN} in server: {RESET}{BLUE}{server_name}{RESET}")
                
                # Clean up the queued message for the song that's about to play
                if server_music_bot.current_song['url'] in server_music_bot.queued_messages:
                    try:
                        await server_music_bot.queued_messages[server_music_bot.current_song['url']].delete()
                        del server_music_bot.queued_messages[server_music_bot.current_song['url']]
                    except Exception as e:
                        print(f"Error deleting queued message: {str(e)}")

                if not server_music_bot.current_song.get('is_stream'):
                    # Check if file exists and download is complete
                    if not os.path.exists(server_music_bot.current_song['file_path']):
                        print(f"Error: File not found: {server_music_bot.current_song['file_path']}")
                        if len(server_music_bot.queue) > 0:
                            await process_queue(server_music_bot, ctx)  # Recursively try the next song
                        return
                        
                    # If we have a download progress object, wait for download to complete
                    if hasattr(server_music_bot, 'download_progress') and server_music_bot.download_progress:
                        max_wait = 5  # Maximum seconds to wait
                        start_time = time.time()
                        while not server_music_bot.download_progress.download_complete:
                            if time.time() - start_time > max_wait:
                                print("Warning: Download taking too long, proceeding anyway")
                                break
                            await asyncio.sleep(0.1)

                # Check if voice client is connected, reconnect if needed
                if not server_music_bot.voice_client or not server_music_bot.voice_client.is_connected():
                    print("Voice client not connected, attempting to reconnect...")
                    connected = await server_music_bot.join_voice_channel(ctx)
                    if not connected:
                        print("Failed to reconnect to voice channel")
                        server_music_bot.voice_client = None
                        
                        # Attempt automatic restart if reconnection fails
                        try:
                            await ctx.send("⚠️ Internal error detected!. Automatically restarting bot...")
                            restart_cog = server_music_bot.bot.get_cog('Restart')
                            if restart_cog:
                                await restart_cog.restart_cmd(ctx)
                        except Exception as e:
                            print(f"Error during automatic restart in play_next: {str(e)}")
                        return
                else:
                    # Handle previous now playing message
                    if server_music_bot.now_playing_message:
                        try:
                            # Add null check for bot instance
                            if server_music_bot.bot:
                                # Add null check before accessing the cog
                                loop_cog = server_music_bot.bot.get_cog('Loop') if hasattr(server_music_bot.bot, 'get_cog') else None
                                is_looped = loop_cog and previous_song and previous_song['url'] in loop_cog.looped_songs if loop_cog else False

                                # For looped songs that weren't skipped, just delete the message
                                if is_looped and not (hasattr(server_music_bot, 'was_skipped') and server_music_bot.was_skipped):
                                    await server_music_bot.now_playing_message.delete()
                                else:
                                    # For non-looped songs or skipped songs, show appropriate message
                                    title = "Skipped song" if hasattr(server_music_bot, 'was_skipped') and server_music_bot.was_skipped else "Finished playing"
                                    description = f"[{previous_song['title']}]({previous_song['url']})"
                                    
                                    # Create a context-like object with the requester information
                                    class DummyCtx:
                                        def __init__(self, author):
                                            self.author = author
                                    
                                    # Use the original requester if available, otherwise use the context
                                    # For playlist songs, the requester is stored in the song info
                                    requester = previous_song.get('requester', ctx.author)
                                    ctx_with_requester = DummyCtx(requester) if requester else ctx
                                    
                                    finished_embed = create_embed(
                                        title,
                                        description,
                                        color=0x808080,  # Gray color for finished
                                        thumbnail_url=previous_song.get('thumbnail'),
                                        ctx=ctx_with_requester
                                    )
                                    # Don't include view for status messages
                                    await server_music_bot.now_playing_message.edit(embed=finished_embed, view=None)
                                    
                                    # Reset the skip flag after handling the previous song
                                    if hasattr(server_music_bot, 'was_skipped'):
                                        server_music_bot.was_skipped = False
                        except Exception as e:
                            print(f"Error updating previous now playing message: {str(e)}")

                    # Create a context-like object with the requester information for the current song
                    class DummyCtx:
                        def __init__(self, author):
                            self.author = author
                    
                    # Use the original requester if available, otherwise use the context
                    requester = server_music_bot.current_song.get('requester', ctx.author)
                    ctx_with_requester = DummyCtx(requester) if requester else ctx

                    # Check if we should send the now playing message
                    if should_send_now_playing(server_music_bot, server_music_bot.current_song['title']):
                        now_playing_embed = create_embed(
                            "Now playing 🎵",
                            f"[{server_music_bot.current_song['title']}]({server_music_bot.current_song['url']})",
                            color=0x00ff00,
                            thumbnail_url=server_music_bot.current_song.get('thumbnail'),
                            ctx=ctx_with_requester
                        )
                        # Create view with buttons if enabled
                        view = create_now_playing_view()
                        # Only pass the view if it's not None
                        kwargs = {'embed': now_playing_embed}
                        if view is not None:
                            kwargs['view'] = view
                        server_music_bot.now_playing_message = await ctx.send(**kwargs)
                    
                    # Update bot presence
                    try:
                        if server_music_bot.bot:
                            await update_activity(server_music_bot.bot, server_music_bot.current_song, is_playing=True)
                    except Exception as e:
                        print(f"Error updating presence: {str(e)}")
                    
                    server_music_bot.current_command_msg = None
                    server_music_bot.current_command_author = None

                    try:
                        # Check if already playing before attempting to play
                        if server_music_bot.voice_client and server_music_bot.voice_client.is_playing():
                            print("Already playing audio, stopping current playback")
                            server_music_bot.voice_client.stop()
                            
                        if server_music_bot.voice_client and server_music_bot.voice_client.is_connected():
                            audio_source = discord.FFmpegPCMAudio(
                                server_music_bot.current_song['file_path'],
                                **FFMPEG_OPTIONS
                            )
                            # Call read() on the audio source before playing to prevent speed-up issue
                            audio_source.read()
                            # Set the playback start time right before starting playback
                            server_music_bot.playback_start_time = time.time()
                            server_music_bot.playback_state = "playing"
                            server_music_bot.voice_client.play(
                                audio_source,
                                after=lambda e: asyncio.run_coroutine_threadsafe(
                                    server_music_bot.after_playing_coro(e, ctx), 
                                    server_music_bot.bot_loop or asyncio.get_event_loop()
                                )
                            )
                    except Exception as e:
                        print(f"Error starting playback: {str(e)}")
                        if len(server_music_bot.queue) > 0:
                            await process_queue(server_music_bot, ctx)
            except Exception as e:
                print(f"Error in play_next: {str(e)}")
                if len(server_music_bot.queue) > 0:
                    await process_queue(server_music_bot, ctx)
        else:
            server_music_bot.current_song = None
            # Update activity
            if server_music_bot.bot:
                await update_activity(server_music_bot.bot)
            if server_music_bot.download_queue.empty():
                if server_music_bot.voice_client and server_music_bot.voice_client.is_connected():
                    await server_music_bot.voice_client.disconnect()