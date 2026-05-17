import discord
from discord.ui import Button, View
import asyncio
import os
import time
from scripts.messages import create_embed, should_send_now_playing
from scripts.config import load_config, FFMPEG_OPTIONS
from scripts.ui_components import create_now_playing_view
from scripts.constants import RED, GREEN, BLUE, RESET, EMBED_COLOR_FINISHED
from scripts.process_queue import process_queue
from scripts.activity import update_activity
from scripts.playback import (
    RequesterContext,
    cleanup_queued_message,
    verify_audio_file,
    get_requester_context,
    send_now_playing_message,
    update_bot_presence,
    create_audio_source,
    create_after_callback,
    log_now_playing,
    is_bot_explicitly_stopped,
)

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
    
    # Check if context is valid
    if not ctx or not hasattr(ctx, 'guild') or not ctx.guild:
        print("Error in play_next: Invalid context provided")
        return
        
    # Get server-specific music bot instance
    server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
    
    # Use the playback lock to prevent race conditions
    async with server_music_bot.playback_lock:
        # Check if the bot has been explicitly stopped
        if is_bot_explicitly_stopped(server_music_bot):
            async with server_music_bot.queue_lock:
                server_music_bot.queue.clear()
            return
            
        if server_music_bot.queue:
            try:
                # Store the previous song for reference
                previous_song = server_music_bot.current_song
                # Get the next song from the queue (use queue_lock for thread safety)
                async with server_music_bot.queue_lock:
                    server_music_bot.current_song = server_music_bot.queue.popleft()
                # Store the context in the current_song for later use
                server_music_bot.current_song['ctx'] = ctx
                # Update last activity time to prevent inactivity timeout
                server_music_bot.last_activity = time.time()
                
                # Log now playing
                server_name = ctx.guild.name if ctx and hasattr(ctx, 'guild') and ctx.guild else "Unknown Server"
                log_now_playing(server_music_bot.current_song['title'], server_name)
                
                # Clean up the queued message
                await cleanup_queued_message(server_music_bot, server_music_bot.current_song['url'])

                # Verify audio file exists (for non-streams)
                if not server_music_bot.current_song.get('is_stream'):
                    if not verify_audio_file(server_music_bot.current_song['file_path']):
                        print(f"Error: File not found: {server_music_bot.current_song['file_path']}")
                        if server_music_bot.queue:
                            await process_queue(server_music_bot, ctx)
                        return
                        
                    # Wait for download to complete if needed
                    if hasattr(server_music_bot, 'download_progress') and server_music_bot.download_progress:
                        max_wait = 5
                        start_time = time.time()
                        while not server_music_bot.download_progress.download_complete:
                            if time.time() - start_time > max_wait:
                                print("Warning: Download taking too long, proceeding anyway")
                                break
                            await asyncio.sleep(0.1)

                # Check if voice client is connected, reconnect if needed
                if not server_music_bot.voice_client or not server_music_bot.voice_client.is_connected():
                    print("Voice client not connected, attempting to reconnect...")
                    connected = False
                    try:
                        connected = await server_music_bot.join_voice_channel(ctx)
                    except Exception as e:
                        print(f"Error joining voice channel: {str(e)}")
                        
                    if not connected:
                        print("Failed to reconnect to voice channel")
                        server_music_bot.voice_client = None
                        
                        # Store the current song back in the queue
                        if server_music_bot.current_song:
                            server_music_bot.queue.appendleft(server_music_bot.current_song)
                            server_music_bot.current_song = None
                        print("Voice connection failed. Please try again later or use !join to reconnect manually.")
                        return
                else:
                    # Handle previous now playing message
                    if server_music_bot.now_playing_message:
                        await _update_previous_song_message(server_music_bot, previous_song, ctx)

                    # Send now playing message
                    await send_now_playing_message(server_music_bot, server_music_bot.current_song, ctx)
                    
                    # Update bot presence
                    await update_bot_presence(server_music_bot, server_music_bot.current_song, is_playing=True)
                    
                    # Reset command tracking
                    server_music_bot.current_command_msg = None
                    server_music_bot.current_command_author = None

                    try:
                        # Check if already playing
                        if server_music_bot.voice_client and server_music_bot.voice_client.is_playing():
                            print("Already playing audio, stopping current playback")
                            server_music_bot.voice_client.stop()
                            
                        # Double-check voice client is still connected
                        if not server_music_bot.voice_client or not server_music_bot.voice_client.is_connected():
                            print("Voice client disconnected just before playback, aborting")
                            if server_music_bot.current_song:
                                server_music_bot.queue.appendleft(server_music_bot.current_song)
                            return
                        
                        # Create audio source and start playback
                        audio_source = create_audio_source(
                            server_music_bot.current_song['file_path'],
                            use_volume_transformer=False
                        )
                        
                        # Set playback state
                        server_music_bot.playback_start_time = time.time()
                        server_music_bot.playback_state = "playing"
                        
                        # Create callback and play
                        after_callback = create_after_callback(server_music_bot, ctx)
                        
                        if server_music_bot.voice_client and server_music_bot.voice_client.is_connected():
                            server_music_bot.voice_client.play(audio_source, after=after_callback)
                        else:
                            print("Voice client became invalid during playback setup")
                            if server_music_bot.current_song:
                                server_music_bot.queue.appendleft(server_music_bot.current_song)
                    except Exception as e:
                        print(f"Error starting playback: {str(e)}")
                        if server_music_bot.queue:
                            await process_queue(server_music_bot, ctx)
            except Exception as e:
                print(f"Error in play_next: {str(e)}")
                if server_music_bot.queue:
                    await process_queue(server_music_bot, ctx)
        else:
            server_music_bot.current_song = None
            # Update activity
            if server_music_bot.bot:
                await update_activity(server_music_bot.bot)
            if server_music_bot.download_queue.empty():
                if server_music_bot.voice_client and server_music_bot.voice_client.is_connected():
                    await server_music_bot.voice_client.disconnect()


async def _update_previous_song_message(server_music_bot, previous_song, ctx):
    """
    Update the previous now playing message when transitioning to a new song.
    
    Args:
        server_music_bot: The MusicBot instance
        previous_song: The previous song dict
        ctx: The context
    """
    if not previous_song:
        return
        
    try:
        if not server_music_bot.bot:
            return
            
        loop_cog = server_music_bot.bot.get_cog('Loop') if hasattr(server_music_bot.bot, 'get_cog') else None
        is_looped = loop_cog and previous_song['url'] in loop_cog.looped_songs if loop_cog else False

        # For looped songs that weren't skipped, just delete the message
        if is_looped and not (hasattr(server_music_bot, 'was_skipped') and server_music_bot.was_skipped):
            await server_music_bot.now_playing_message.delete()
        else:
            # For non-looped songs or skipped songs, show appropriate message
            title = "Skipped song" if hasattr(server_music_bot, 'was_skipped') and server_music_bot.was_skipped else "Finished playing"
            description = f"[{previous_song['title']}]({previous_song['url']})"
            
            # Use the original requester if available
            requester = previous_song.get('requester', ctx.author)
            ctx_with_requester = RequesterContext(requester) if requester else ctx
            
            finished_embed = create_embed(
                title,
                description,
                color=EMBED_COLOR_FINISHED,
                thumbnail_url=previous_song.get('thumbnail'),
                ctx=ctx_with_requester
            )
            await server_music_bot.now_playing_message.edit(embed=finished_embed, view=None)
            
            # Reset the skip flag
            if hasattr(server_music_bot, 'was_skipped'):
                server_music_bot.was_skipped = False
    except Exception as e:
        print(f"Error updating previous now playing message: {str(e)}")