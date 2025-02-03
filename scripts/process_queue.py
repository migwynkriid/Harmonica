import discord
import asyncio
import time
from pathlib import Path
from scripts.duration import get_audio_duration
from scripts.messages import create_embed, should_send_now_playing
from scripts.config import FFMPEG_OPTIONS, load_config
from scripts.ui_components import create_now_playing_view

# Get default volume from config
config = load_config()
DEFAULT_VOLUME = config.get('DEFAULT_VOLUME', 100)

async def process_queue(music_bot):
    """Process the song queue"""
    if not music_bot:
        return
        
    if music_bot.waiting_for_song or not music_bot.queue:
        return

    music_bot.waiting_for_song = True

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
                # Clear the current song and reset states
                music_bot.current_song = None
                music_bot.is_playing = False
                music_bot.voice_client = None
                music_bot.waiting_for_song = False
            except Exception as e:
                print(f"Error during voice connection cleanup: {str(e)}")
            return

        if song['url'] in music_bot.queued_messages:
            try:
                await music_bot.queued_messages[song['url']].delete()
            except Exception as e:
                print(f"Error deleting queue message: {str(e)}")
            finally:
                del music_bot.queued_messages[song['url']]

        music_bot.current_song = song
        music_bot.is_playing = True
        music_bot.playback_start_time = time.time()  # Set the start time when song begins playing
        
        # Get and store the actual duration using ffprobe
        if not song.get('is_stream'):
            duration = get_audio_duration(song['file_path'])
            music_bot.current_song['duration'] = duration
        
        # Only send now playing message if we should
        if should_send_now_playing(music_bot, song['title']):
            now_playing_embed = create_embed(
                "Now playing 🎵",
                f"[{song['title']}]({song['url']})",
                color=0x00ff00,
                thumbnail_url=song.get('thumbnail'),
                ctx=ctx
            )

            # Create and send the message with the view if buttons are enabled
            view = create_now_playing_view()
            # Only pass the view if it's not None
            kwargs = {'embed': now_playing_embed}
            if view is not None:
                kwargs['view'] = view
            music_bot.now_playing_message = await ctx.send(**kwargs)
        
        await music_bot.bot.change_presence(activity=discord.Game(name=f"{song['title']}"))
        
        audio_source = discord.FFmpegOpusAudio(
            song['file_path'],
            **FFMPEG_OPTIONS
        )
        # Call read() on the audio source before playing to prevent speed-up issue
        audio_source.read()

        current_message = music_bot.now_playing_message
        current_song_info = {
            'title': song['title'],
            'url': song['url'],
            'thumbnail': song.get('thumbnail')
        }

        def after_playing(error):
            """Callback after song finishes"""
            if error:
                print(f"Error in playback: {error}")
            
            async def update_now_playing():
                try:
                    if current_message:
                        # Check if the song is looped
                        loop_cog = music_bot.bot.get_cog('Loop')
                        is_looped = loop_cog and current_song_info['url'] in loop_cog.looped_songs

                        # For looped songs that weren't skipped, just delete the message
                        if is_looped and not music_bot.was_skipped:
                            await current_message.delete()
                        else:
                            # For non-looped songs or skipped songs, show appropriate message
                            title = "Skipped song" if music_bot.was_skipped else "Finished playing"
                            
                            finished_embed = create_embed(
                                title,
                                f"[{current_song_info['title']}]({current_song_info['url']})",
                                color=0x808080,
                                thumbnail_url=current_song_info.get('thumbnail'),
                                ctx=ctx
                            )
                            # Remove buttons when song is finished
                            await current_message.edit(embed=finished_embed, view=None)
                    
                    music_bot.is_playing = False
                    music_bot.waiting_for_song = False
                    music_bot.current_song = None
                    music_bot.now_playing_message = None
                    music_bot.was_skipped = False  # Reset the skipped flag
                    from scripts.config import load_config
                    prefix = load_config()['PREFIX']
                    await music_bot.bot.change_presence(activity=discord.Game(name=f"nothing! use {prefix}play"))
                    await process_queue(music_bot)
                except Exception as e:
                    print(f"Error updating finished message: {str(e)}")
            
            asyncio.run_coroutine_threadsafe(update_now_playing(), music_bot.bot_loop)

        music_bot.voice_client.play(audio_source, after=after_playing)

    except Exception as e:
        print(f"Error in process_queue: {str(e)}")
        music_bot.waiting_for_song = False
        if not music_bot.is_playing:
            await process_queue(music_bot)
    finally:
        music_bot.waiting_for_song = False
        if not music_bot.is_playing:
            await process_queue(music_bot)