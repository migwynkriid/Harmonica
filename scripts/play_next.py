import discord
from discord.ui import Button, View
import asyncio
import os
import time
from scripts.messages import create_embed, should_send_now_playing
from scripts.config import load_config, FFMPEG_OPTIONS
from scripts.ui_components import create_now_playing_view

# Get default volume from config
config = load_config()
DEFAULT_VOLUME = config.get('DEFAULT_VOLUME', 100)

async def play_next(ctx):
    """Play the next song in the queue"""
    from bot import music_bot
    
    # Add playback lock to prevent race conditions
    if hasattr(music_bot, 'playback_lock'):
        playback_lock = music_bot.playback_lock
    else:
        playback_lock = asyncio.Lock()
        music_bot.playback_lock = playback_lock
    
    async with playback_lock:
        if len(music_bot.queue) > 0:
            try:
                previous_song = music_bot.current_song
                music_bot.current_song = music_bot.queue.pop(0)
                music_bot.last_activity = time.time()
                print(f"Playing next song: {music_bot.current_song['title']}")
                
                # Clean up the queued message for the song that's about to play
                if music_bot.current_song['url'] in music_bot.queued_messages:
                    try:
                        await music_bot.queued_messages[music_bot.current_song['url']].delete()
                        del music_bot.queued_messages[music_bot.current_song['url']]
                    except Exception as e:
                        print(f"Error deleting queued message: {str(e)}")

                if not music_bot.current_song.get('is_stream'):
                    if not os.path.exists(music_bot.current_song['file_path']):
                        print(f"Error: File not found: {music_bot.current_song['file_path']}")
                        if len(music_bot.queue) > 0:
                            await play_next(ctx)
                        return

                if not music_bot.voice_client or not music_bot.voice_client.is_connected():
                    print("Voice client not connected, attempting to reconnect...")
                    connected = await music_bot.join_voice_channel(ctx)
                    if not connected:
                        print("Failed to reconnect to voice channel")
                        music_bot.voice_client = None
                        
                        try:
                            await ctx.send("⚠️ Internal error detected!. Automatically restarting bot...")
                            restart_cog = music_bot.bot.get_cog('Restart')
                            if restart_cog:
                                await restart_cog.restart_cmd(ctx)
                        except Exception as e:
                            print(f"Error during automatic restart in play_next: {str(e)}")
                        return
                else:
                    if music_bot.now_playing_message:
                        try:
                            # Check if the song is looped
                            loop_cog = music_bot.bot.get_cog('Loop')
                            is_looped = loop_cog and previous_song['url'] in loop_cog.looped_songs

                            # For looped songs that weren't skipped, just delete the message
                            if is_looped and not (hasattr(music_bot, 'was_skipped') and music_bot.was_skipped):
                                await music_bot.now_playing_message.delete()
                            else:
                                # For non-looped songs or skipped songs, show appropriate message
                                title = "Skipped song" if hasattr(music_bot, 'was_skipped') and music_bot.was_skipped else "Finished playing"
                                description = f"[🎵 {previous_song['title']}]({previous_song['url']})"
                                
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
                                await music_bot.now_playing_message.edit(embed=finished_embed, view=None)
                        except Exception as e:
                            print(f"Error updating previous now playing message: {str(e)}")

                    # Create a context-like object with the requester information for the current song
                    class DummyCtx:
                        def __init__(self, author):
                            self.author = author
                    
                    # Use the original requester if available, otherwise use the context
                    requester = music_bot.current_song.get('requester', ctx.author)
                    ctx_with_requester = DummyCtx(requester) if requester else ctx

                    # Check if we should send the now playing message
                    if should_send_now_playing(music_bot, music_bot.current_song['title']):
                        now_playing_embed = create_embed(
                            "Now playing 🎵",
                            f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})",
                            color=0x00ff00,
                            thumbnail_url=music_bot.current_song.get('thumbnail'),
                            ctx=ctx_with_requester
                        )
                        # Create view with buttons if enabled
                        view = create_now_playing_view()
                        # Only pass the view if it's not None
                        kwargs = {'embed': now_playing_embed}
                        if view is not None:
                            kwargs['view'] = view
                        music_bot.now_playing_message = await ctx.send(**kwargs)
                    
                    await music_bot.bot.change_presence(activity=discord.Game(name=f"{music_bot.current_song['title']}"))
                    
                    music_bot.current_command_msg = None
                    music_bot.current_command_author = None

                    try:
                        # Check if already playing before attempting to play
                        if music_bot.voice_client and music_bot.voice_client.is_playing():
                            print("Already playing audio, stopping current playback")
                            music_bot.voice_client.stop()
                            await asyncio.sleep(0.5)  # Small delay to ensure clean stop
                            
                        # Add delay before starting new song to ensure clean state
                        await asyncio.sleep(0.5)
                            
                        if music_bot.voice_client and music_bot.voice_client.is_connected():
                            audio_source = discord.FFmpegOpusAudio(
                                music_bot.current_song['file_path'],
                                **FFMPEG_OPTIONS
                            )
                            # Call read() on the audio source before playing to prevent speed-up issue
                            audio_source.read()
                            # Set the playback start time right before starting playback
                            music_bot.playback_start_time = time.time()
                            music_bot.voice_client.play(
                                audio_source,
                                after=lambda e: asyncio.run_coroutine_threadsafe(
                                    music_bot.after_playing_coro(e, ctx), 
                                    music_bot.bot_loop
                                )
                            )
                    except Exception as e:
                        print(f"Error starting playback: {str(e)}")
                        if len(music_bot.queue) > 0:
                            await play_next(ctx)
            except Exception as e:
                print(f"Error in play_next: {str(e)}")
                if len(music_bot.queue) > 0:
                    await play_next(ctx)
        else:
            music_bot.current_song = None
            music_bot.update_activity()
            await music_bot.bot.change_presence(activity=discord.Game(name="nothing! use !play "))
            if music_bot.download_queue.empty():
                if music_bot.voice_client and music_bot.voice_client.is_connected():
                    await music_bot.voice_client.disconnect()