import asyncio
import discord
import yt_dlp
import os
import json
import random
from pathlib import Path
from scripts.play_next import play_next
from scripts.config import load_config, BASE_YTDL_OPTIONS, config_vars
from scripts.messages import update_or_send_message, create_embed
from scripts.duration import get_audio_duration

class PlaylistHandler:
    async def _process_playlist_downloads(self, entries, ctx, status_msg=None):
        """Process remaining playlist videos in the background"""
        try:
            total_entries = len(entries)
            processed_entries = 0
            failed_entries = 0
            
            for entry in entries:
                if entry:
                    # Check if bot is still in voice chat
                    if not self.voice_client or not self.voice_client.is_connected():
                        await self.cancel_downloads()
                        if status_msg:
                            try:
                                await status_msg.delete()
                            except:
                                pass
                        return
                        
                    try:
                        video_url = f"https://youtube.com/watch?v={entry['id']}"
                        song_info = await self.download_song(video_url, status_msg=None)
                        if song_info:
                            # Get duration using ffprobe asynchronously
                            song_info['duration'] = await get_audio_duration(song_info['file_path'])
                            song_info['requester'] = ctx.author
                            song_info['is_from_playlist'] = True
                            async with self.queue_lock:
                                self.queue.append(song_info)
                                if not self.is_playing and not self.voice_client.is_playing() and len(self.queue) == 1:
                                    await play_next(ctx)
                            processed_entries += 1
                        else:
                            failed_entries += 1

                    except Exception as e:
                        print(f"Error downloading song {entry.get('id', 'unknown')}: {str(e)}")
                        failed_entries += 1
                        continue  # Skip this song and continue with the next one

        except Exception as e:
            print(f"Error in playlist download processing: {str(e)}")

    async def _handle_playlist(self, url, ctx, status_msg=None):
        """Handle a YouTube playlist by extracting video links and downloading them sequentially"""
        try:
            # Use BASE_YTDL_OPTIONS and override only what's needed for playlist extraction
            ydl_opts = BASE_YTDL_OPTIONS.copy()
            ydl_opts.update({
                'extract_flat': 'in_playlist',  # Only extract video metadata for playlist items
                'format': None,  # Don't need format for playlist extraction
                'download': False  # Don't download during playlist extraction
            })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                
                if not info or not info.get('entries'):
                    raise Exception("Could not extract playlist information")

                entries = info['entries']
                total_videos = len(entries)

                # Shuffle entries if enabled
                if config_vars.get('DOWNLOADS', {}).get('SHUFFLE_DOWNLOAD', False):
                    random.shuffle(entries)

                if status_msg:
                    playlist_title = info.get('title', 'Unknown')
                    playlist_url = info.get('webpage_url', url)
                    description = f"Playlist: [{playlist_title}]({playlist_url})\nEntries: {total_videos}"
                    playlist_embed = create_embed(
                        "Processing Playlist",
                        description,
                        color=0x3498db,
                        ctx=ctx
                    )
                    # Try different thumbnail sources
                    thumbnail_url = info.get('thumbnails', [{}])[0].get('url') if info.get('thumbnails') else None
                    if not thumbnail_url:
                        thumbnail_url = info.get('thumbnail')
                    if thumbnail_url:
                        playlist_embed.set_thumbnail(url=thumbnail_url)
                    await status_msg.edit(embed=playlist_embed)
                    await status_msg.delete(delay=10)  

                if not self.voice_client or not self.voice_client.is_connected():
                    await self.join_voice_channel(ctx)

                if entries:
                    # Process all entries using _process_playlist_downloads
                    await self._process_playlist_downloads(entries, ctx)
                    return True

                return False

        except Exception as e:
            print(f"Error processing playlist: {str(e)}")
            if status_msg:
                error_embed = create_embed(
                    "Error",
                    f"Failed to process playlist: {str(e)}",
                    color=0xe74c3c,
                    ctx=status_msg.channel
                )
                await status_msg.edit(embed=error_embed)
            return False

    async def _queue_playlist_videos(self, entries, ctx, is_from_playlist, status_msg, ydl_opts, playlist_title, playlist_url, total_videos):
        """Process remaining playlist videos in the background"""
        try:
            for entry in entries:
                if entry:
                    video_url = f"https://youtube.com/watch?v={entry['id']}"
                    song_info = await self.download_song(video_url, status_msg=None)
                    if song_info:
                        song_info['requester'] = ctx.author
                        song_info['is_from_playlist'] = True
                        async with self.queue_lock:
                            self.queue.append(song_info)
                            if not self.is_playing and not self.voice_client.is_playing() and len(self.queue) == 1:
                                await play_next(ctx)


        except Exception as e:
            print(f"Error in playlist download processing: {str(e)}")