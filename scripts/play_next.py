import discord
from discord.ui import Button, View
import asyncio
import os
import time
from scripts.messages import create_embed
from scripts.config import load_config
from scripts.ui_components import create_now_playing_view

# Get default volume from config
config = load_config()
DEFAULT_VOLUME = config.get('DEFAULT_VOLUME', 100)

async def play_next(ctx):
    """Play the next song in the queue"""
    from __main__ import music_bot
    
    if len(music_bot.queue) > 0:
        try:
            previous_song = music_bot.current_song
            music_bot.current_song = music_bot.queue.pop(0)
            music_bot.last_activity = time.time()
            print(f"Playing next song: {music_bot.current_song['title']}")
            
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
                if music_bot.now_playing_message and not music_bot.was_skipped:
                    try:
                        finished_embed = create_embed(
                            "Finished playing",
                            f"[🎵 {previous_song['title']}]({previous_song['url']})",
                            color=0x808080,  # Gray color for finished
                            thumbnail_url=previous_song.get('thumbnail'),
                            ctx=ctx
                        )
                        # Don't include view for status messages
                        await music_bot.now_playing_message.edit(embed=finished_embed, view=None)
                    except Exception as e:
                        print(f"Error updating previous now playing message: {str(e)}")

                now_playing_embed = create_embed(
                    "Now playing 🎵",
                    f"[{music_bot.current_song['title']}]({music_bot.current_song['url']})",
                    color=0x00ff00,
                    thumbnail_url=music_bot.current_song.get('thumbnail'),
                    ctx=ctx
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
                    if music_bot.voice_client and music_bot.voice_client.is_connected():
                        ffmpeg_options = {
                            'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                        }
                        audio_source = discord.FFmpegPCMAudio(
                            music_bot.current_song['file_path'],
                            **ffmpeg_options
                        )
                        # Convert DEFAULT_VOLUME from percentage (0-100) to float (0.0-2.0)
                        default_volume = DEFAULT_VOLUME / 50.0  # This makes 100% = 2.0, 50% = 1.0, etc.
                        audio_source = discord.PCMVolumeTransformer(audio_source, volume=default_volume)
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