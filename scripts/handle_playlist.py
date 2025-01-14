import asyncio
import discord
import yt_dlp
import os
import json
from pathlib import Path
from scripts.play_next import play_next
from scripts.config import load_config
from scripts.messages import update_or_send_message, create_embed

class PlaylistHandler:
    async def _process_playlist_downloads(self, entries, ctx, status_msg=None):
        """Process remaining playlist videos in the background"""
        try:
            for entry in entries:
                if entry:
                    video_url = f"https://youtube.com/watch?v={entry['id']}"
                    song_info = await self.download_song(video_url, status_msg=None)
                    if song_info:
                        async with self.queue_lock:
                            self.queue.append(song_info)
                            if not self.is_playing and not self.voice_client.is_playing():
                                await play_next(ctx)

            if status_msg:
                final_embed = create_embed(
                    "Playlist Complete",
                    f"All songs have been downloaded and queued",
                    color=0x00ff00,
                    ctx=status_msg.channel
                )
                try:
                    await status_msg.edit(embed=final_embed)
                    await status_msg.delete(delay=5)
                except:
                    pass

        except Exception as e:
            print(f"Error in playlist download processing: {str(e)}")

    async def _handle_playlist(self, url, ctx, status_msg=None):
        """Handle a YouTube playlist by extracting video links and downloading them sequentially"""
        try:
            ydl_opts = {
                'extract_flat': True,
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                
                if not info or not info.get('entries'):
                    raise Exception("Could not extract playlist information")

                total_videos = len(info['entries'])

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
                    if info.get('thumbnail'):
                        playlist_embed.set_thumbnail(url=info['thumbnail'])
                    await status_msg.edit(embed=playlist_embed)

                if not self.voice_client or not self.voice_client.is_connected():
                    await self.join_voice_channel(ctx)

                if info['entries']:
                    first_entry = info['entries'][0]
                    if first_entry:
                        first_url = f"https://youtube.com/watch?v={first_entry['id']}"
                        first_song = await self.download_song(first_url, status_msg=None)
                        if first_song:
                            self.queue.append(first_song)
                            if not self.is_playing:
                                await play_next(ctx)

                if len(info['entries']) > 1:
                    asyncio.create_task(self._process_playlist_downloads(info['entries'][1:], ctx, status_msg))

                return True

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
                        async with self.queue_lock:
                            self.queue.append(song_info)
                            if not self.is_playing and not self.voice_client.is_playing():
                                await play_next(ctx)

            if status_msg:
                final_embed = create_embed(
                    "Playlist Complete",
                    f"All songs have been downloaded and queued",
                    color=0x00ff00,
                    ctx=status_msg.channel
                )
                try:
                    await status_msg.edit(embed=final_embed)
                    await status_msg.delete(delay=5)
                except:
                    pass

        except Exception as e:
            print(f"Error in playlist download processing: {str(e)}")