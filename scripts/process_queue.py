import discord
import asyncio
import time
from pathlib import Path
from scripts.duration import get_audio_duration
from scripts.messages import create_embed
from scripts.config import FFMPEG_OPTIONS, load_config

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
            print("Not connected to voice during process_queue")
            try:
                if ctx:
                    await ctx.send("⚠️ Voice connection lost. Automatically restarting bot...")
                
                restart_cog = music_bot.bot.get_cog('Restart')
                if restart_cog:
                    await restart_cog.restart_cmd(ctx)
            except Exception as e:
                print(f"Error during automatic restart in process_queue: {str(e)}")
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
        
        now_playing_embed = create_embed(
            "Now playing 🎵",
            f"[{song['title']}]({song['url']})",
            color=0x00ff00,
            thumbnail_url=song.get('thumbnail'),
            ctx=ctx
        )
        music_bot.now_playing_message = await ctx.send(embed=now_playing_embed)
        
        await music_bot.bot.change_presence(activity=discord.Game(name=f"{song['title']}"))
        
        if song.get('is_stream'):
            audio_source = discord.FFmpegPCMAudio(
                song['file_path'],
                **FFMPEG_OPTIONS
            )
        else:
            audio_source = discord.FFmpegPCMAudio(
                song['file_path'],
                **FFMPEG_OPTIONS
            )

        # Convert DEFAULT_VOLUME from percentage (0-100) to float (0.0-2.0)
        default_volume = DEFAULT_VOLUME / 50.0  # This makes 100% = 2.0, 50% = 1.0, etc.
        audio_source = discord.PCMVolumeTransformer(audio_source, volume=default_volume)

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
                        finished_embed = create_embed(
                            "Finished playing",
                            f"[{current_song_info['title']}]({current_song_info['url']})",
                            color=0x808080,
                            thumbnail_url=current_song_info.get('thumbnail'),
                            ctx=ctx
                        )
                        await current_message.edit(embed=finished_embed)
                    
                    music_bot.is_playing = False
                    music_bot.waiting_for_song = False
                    music_bot.current_song = None
                    music_bot.now_playing_message = None
                    await music_bot.bot.change_presence(activity=discord.Game(name="nothing! use !play "))
                    await process_queue(music_bot)
                except Exception as e:
                    print(f"Error updating finished message: {str(e)}")
            
            asyncio.run_coroutine_threadsafe(update_now_playing(), music_bot.bot_loop)

        music_bot.voice_client.play(audio_source, after=after_playing)

    finally:
        music_bot.waiting_for_song = False
        if not music_bot.is_playing:
            await process_queue(music_bot)