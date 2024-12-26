import asyncio
import discord
import yt_dlp
import os
import json

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

YTDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a][abr<=96]/bestaudio[abr<=96]/bestaudio/best/bestaudio*',
    'outtmpl': '%(id)s.%(ext)s',
    'extract_audio': True,
    'audio_format': 'mp3',
    'audio_quality': '96K',
    'no_warnings': True,
    'quiet': True,
    'no_color': True,
    'progress_hooks': [],
    'cookiefile': 'cookies.txt',
    'ignoreerrors': True,
    'no_check_certificate': True,
    'source_address': '0.0.0.0',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '96',
    }],
}

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
                                await self.play_next(ctx)

            if status_msg:
                final_embed = self.create_embed(
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
                    playlist_embed = self.create_embed(
                        "Processing Playlist",
                        f"Extracted {total_videos} links. Starting downloads...",
                        color=0x3498db,
                        ctx=ctx
                    )
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
                                await self.play_next(ctx)

                if len(info['entries']) > 1:
                    asyncio.create_task(self._process_playlist_downloads(info['entries'][1:], ctx, status_msg))

                return True

        except Exception as e:
            print(f"Error processing playlist: {str(e)}")
            if status_msg:
                error_embed = self.create_embed(
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
                                await self.play_next(ctx)

            if status_msg:
                final_embed = self.create_embed(
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