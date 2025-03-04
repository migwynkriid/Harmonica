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
    """
    Handler for processing and managing YouTube playlists.
    
    This class provides methods for extracting, downloading, and queuing
    videos from YouTube playlists. It handles playlist processing in the
    background to allow the first song to start playing immediately.
    """
    
    async def _process_playlist_downloads(self, entries, ctx, status_msg=None):
        """
        Process remaining playlist videos in the background.
        
        This method downloads each video in the playlist and adds it to the queue.
        It runs asynchronously to allow the first song to start playing immediately
        while the rest of the playlist is processed in the background.
        
        Args:
            entries: List of video entries from the playlist
            ctx: Discord command context
            status_msg: Optional message to update with progress
        """
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
                        # Skip URL check for playlist entries since we already verified the playlist
                        song_info = await self.download_song(video_url, status_msg=None, skip_url_check=True)
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
        """
        Handle a YouTube playlist by extracting video links and downloading them sequentially.
        
        This method extracts metadata for all videos in a playlist and then
        processes them in the background using _process_playlist_downloads.
        
        Args:
            url: URL of the playlist
            ctx: Discord command context
            status_msg: Optional message to update with progress
            
        Returns:
            bool: True if playlist processing started successfully, False otherwise
        """
        try:
            # Use BASE_YTDL_OPTIONS and override only what's needed for playlist extraction
            ydl_opts = BASE_YTDL_OPTIONS.copy()
            ydl_opts.update({
                'extract_flat': 'in_playlist',  # Only extract video metadata for playlist items
                'format': None,  # Don't need format for playlist extraction
                'download': False  # Don't download during playlist extraction
            })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract playlist information asynchronously
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                
                if not info or not info.get('entries'):
                    raise Exception("Could not extract playlist information")

                entries = info['entries']
                total_videos = len(entries)

                # Shuffle entries if enabled in config
                if config_vars.get('DOWNLOADS', {}).get('SHUFFLE_DOWNLOAD', False):
                    random.shuffle(entries)

                if status_msg:
                    # Create and display playlist information embed
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

                # Check if bot is still connected to voice
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
        """
        Process remaining playlist videos in the background.
        
        This method downloads each video in the playlist and adds it to the queue.
        It runs asynchronously to allow the first song to start playing immediately
        while the rest of the playlist is processed in the background.
        
        Args:
            entries: List of video entries from the playlist
            ctx: Discord command context
            is_from_playlist: Whether the video is from a playlist
            status_msg: Optional message to update with progress
            ydl_opts: yt_dlp options
            playlist_title: Title of the playlist
            playlist_url: URL of the playlist
            total_videos: Total number of videos in the playlist
        """
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