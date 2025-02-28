import asyncio
import discord
import re
import spotipy
import random
import yt_dlp
from spotipy.oauth2 import SpotifyClientCredentials
import os
from scripts.play_next import play_next
from scripts.process_queue import process_queue
from dotenv import load_dotenv
from scripts.messages import create_embed
from scripts.duration import get_audio_duration
from scripts.config import config_vars
from scripts.caching import playlist_cache
from scripts.constants import RED, GREEN, RESET
from scripts.logging import setup_logging, get_ytdlp_logger, CachedVideoFound

class SpotifyHandler:
    """
    Handler for processing and managing Spotify content.
    
    This class provides methods for extracting track information from Spotify
    URLs (tracks, albums, and playlists) and downloading the corresponding
    audio content via YouTube. It also handles caching of Spotify tracks to
    avoid redundant downloads.
    """
    
    async def handle_spotify_url(self, url, ctx, status_msg=None):
        """
        Handle Spotify URLs by extracting track info and downloading via YouTube.
        
        This method parses a Spotify URL to determine its type (track, album, or playlist)
        and delegates to the appropriate handler method.
        
        Args:
            url: The Spotify URL to process
            ctx: Discord command context
            status_msg: Optional message to update with progress
            
        Returns:
            dict or None: Song information if successful, None otherwise
        """
        try:
            if not self.sp:
                raise ValueError("Spotify functionality is not available. Please check your Spotify credentials in .spotifyenv")

            spotify_match = re.match(r'https://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)', url)
            if not spotify_match:
                raise ValueError("Invalid Spotify URL")

            content_type, content_id = spotify_match.groups()

            if content_type == 'track':
                return await self.handle_spotify_track(content_id, ctx, status_msg)
            elif content_type == 'album':
                return await self.handle_spotify_album(content_id, ctx, status_msg)
            elif content_type == 'playlist':
                return await self.handle_spotify_playlist(content_id, ctx, status_msg)

        except Exception as e:
            print(f"Error handling Spotify URL: {str(e)}")
            if status_msg:
                error_embed = create_embed("Error", f"Failed to process Spotify content: {str(e)}", color=0xe74c3c, ctx=status_msg.channel)
                await status_msg.edit(embed=error_embed)
            return None

    async def handle_spotify_track(self, track_id, ctx, status_msg=None):
        """
        Handle a single Spotify track.
        
        This method first checks if the track is already in the cache.
        If found, it uses the cached file; otherwise, it searches for the track
        on YouTube, downloads it, and adds it to both the cache and the queue.
        
        Args:
            track_id: The Spotify track ID
            ctx: Discord command context
            status_msg: Optional message to update with progress
            
        Returns:
            dict or None: Song information if successful, None otherwise
        """
        try:
            # Check cache first
            cached_info = playlist_cache.get_cached_spotify_track(track_id)
            if cached_info:
                print(f"{GREEN}Found cached Spotify track: {track_id} - {cached_info.get('title', 'Unknown')}{RESET}")
                
                # Delete the "Processing" message if it exists
                if status_msg:
                    try:
                        await status_msg.delete()
                    except discord.NotFound:
                        pass
                    except Exception as e:
                        print(f"Note: Could not delete processing message: {e}")
                
                song_info = {
                    'title': cached_info.get('title', 'Unknown'),
                    'url': cached_info.get('url', f'https://open.spotify.com/track/{track_id}'),
                    'file_path': cached_info['file_path'],
                    'thumbnail': cached_info.get('thumbnail'),
                    'is_from_playlist': False,
                    'requester': ctx.author,
                    'duration': await get_audio_duration(cached_info['file_path']),
                    'ctx': ctx
                }
                self.queue.append(song_info)
                
                if not self.is_playing and not self.voice_client.is_playing():
                    await process_queue(self)
                else:
                    queue_pos = len(self.queue)
                    description = f"[🎵 {song_info['title']}]({song_info['url']})"
                    if self.current_song:
                        loop_cog = ctx.bot.get_cog('Loop')
                        current_song_url = self.current_song['url']
                        is_current_looping = loop_cog and current_song_url in loop_cog.looped_songs
                        if not is_current_looping:
                            description += f"\nPosition in queue: {queue_pos}"
                    
                    queue_embed = create_embed(
                        "Added to Queue",
                        description,
                        color=0x3498db,
                        thumbnail_url=song_info.get('thumbnail'),
                        ctx=ctx
                    )
                    queue_msg = await ctx.send(embed=queue_embed)
                    self.queued_messages[song_info['url']] = queue_msg
                
                return song_info

            # If not in cache, proceed with normal download
            track = self.sp.track(track_id)
            if not track:
                raise ValueError("Could not find track on Spotify")

            artists = ", ".join([artist['name'] for artist in track['artists']])
            search_query = f"{track['name']} {artists}"

            if status_msg:
                await status_msg.edit(embed=create_embed(
                    "Processing",
                    f"Searching for {search_query}",
                    color=0x1DB954,
                    ctx=ctx
                ))

            # First get the YouTube URL without downloading
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'noplaylist': True,
                'extract_flat': True,
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(f"ytsearch1:{search_query}", download=False))
                    if not info or 'entries' not in info or not info['entries']:
                        raise ValueError("No results found")
                        
                    video_info = info['entries'][0]
                    video_url = video_info.get('url') or video_info.get('webpage_url')
                    
                    if not video_url:
                        raise ValueError("Could not get video URL")
                        
                    # Now use download_song with the actual YouTube URL
                    song_info = await self.download_song(video_url, status_msg=status_msg, ctx=ctx)
            except Exception as e:
                print(f"{RED}Error getting YouTube URL: {str(e)}{RESET}")
                return None
            
            # If song is successfully downloaded, cache it and add to queue
            if song_info:
                # Cache the downloaded song with Spotify ID
                playlist_cache.add_spotify_track(
                    track_id,
                    song_info['file_path'],
                    title=song_info['title'],
                    thumbnail=song_info.get('thumbnail'),
                    artist=artists
                )
                print(f"{GREEN}Added Spotify track to cache: {track_id} - {song_info.get('title', 'Unknown')}{RESET}")

                # Add to queue and process as before
                song_info['is_from_playlist'] = False
                song_info['requester'] = ctx.author
                song_info['duration'] = await get_audio_duration(song_info['file_path'])
                song_info['ctx'] = ctx
                self.queue.append(song_info)
                
                # If not currently playing, start playback
                if not self.is_playing and not self.voice_client.is_playing():
                    await process_queue(self)
                else:
                    # Send "Added to Queue" message if we're not starting playback immediately
                    queue_pos = len(self.queue)
                    description = f"[🎵 {song_info['title']}]({song_info['url']})"
                    
                    # Only show position if current song is not looping
                    if self.current_song:
                        loop_cog = ctx.bot.get_cog('Loop')
                        current_song_url = self.current_song['url']
                        is_current_looping = loop_cog and current_song_url in loop_cog.looped_songs
                        if not is_current_looping:
                            description += f"\nPosition in queue: {queue_pos}"
                        
                    queue_embed = create_embed(
                        "Added to Queue",
                        description,
                        color=0x3498db,
                        thumbnail_url=song_info.get('thumbnail'),
                        ctx=ctx
                    )
                    queue_msg = await ctx.send(embed=queue_embed)
                    self.queued_messages[song_info['url']] = queue_msg
            
            return song_info

        except Exception as e:
            print(f"Error handling Spotify track: {str(e)}")
            if status_msg:
                await status_msg.edit(embed=create_embed(
                    "Error",
                    f"Failed to process Spotify track: {str(e)}",
                    color=0xe74c3c,
                    ctx=ctx
                ))
            raise

    async def handle_spotify_album(self, album_id, ctx, status_msg=None):
        """
        Handle a Spotify album.
        
        This method extracts all tracks from a Spotify album and processes them
        in the background, allowing the first track to start playing immediately.
        
        Args:
            album_id: The Spotify album ID
            ctx: Discord command context
            status_msg: Optional message to update with progress
            
        Returns:
            dict or None: Information about the first track if successful, None otherwise
        """
        try:
            album = self.sp.album(album_id)
            if not album:
                raise ValueError("Could not find album on Spotify")

            if status_msg:
                await status_msg.edit(embed=create_embed(
                    "Processing Album",
                    f"Processing album: {album['name']}\nTotal tracks: {album['total_tracks']}",
                    color=0x1DB954,
                    thumbnail_url=album['images'][0]['url'] if album['images'] else None,
                    ctx=ctx
                ))
                await status_msg.delete(delay=5)

            tracks = []
            results = self.sp.album_tracks(album_id)
            tracks.extend(results['items'])
            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])

            # Shuffle tracks if enabled
            if config_vars.get('DOWNLOADS', {}).get('SHUFFLE_DOWNLOAD', False):
                random.shuffle(tracks)

            if tracks:
                first_track = tracks[0]
                track_id = first_track['id']
                artists = ", ".join([artist['name'] for artist in first_track['artists']])
                
                # Check cache first for the first track
                cached_info = playlist_cache.get_cached_spotify_track(track_id)
                if cached_info:
                    print(f"{GREEN}Found cached Spotify track: {track_id} - {cached_info.get('title', 'Unknown')}{RESET}")
                    
                    # Delete the "Processing" message if it exists
                    if status_msg:
                        try:
                            await status_msg.delete()
                        except discord.NotFound:
                            pass
                        except Exception as e:
                            print(f"Note: Could not delete processing message: {e}")
                    
                    song_info = {
                        'title': cached_info.get('title', 'Unknown'),
                        'url': cached_info.get('url', f'https://open.spotify.com/track/{track_id}'),
                        'file_path': cached_info['file_path'],
                        'thumbnail': cached_info.get('thumbnail'),
                        'is_from_playlist': True,
                        'requester': ctx.author,
                        'duration': await get_audio_duration(cached_info['file_path']),
                        'ctx': ctx
                    }
                    self.queue.append(song_info)
                else:
                    # Download if not in cache
                    search_query = f"{first_track['name']} {artists}"
                    song_info = await self.download_song(search_query, status_msg=status_msg, ctx=ctx)
                    if song_info:
                        # Cache the downloaded song with Spotify track ID
                        playlist_cache.add_spotify_track(
                            track_id,
                            song_info['file_path'],
                            title=song_info['title'],
                            thumbnail=song_info.get('thumbnail'),
                            artist=artists
                        )
                        print(f"{GREEN}Added Spotify track to cache: {track_id} - {song_info.get('title', 'Unknown')}{RESET}")
                        
                        # Create a proper queue entry for the first song
                        queue_entry = {
                            'title': song_info.get('title', 'Unknown'),
                            'url': song_info.get('url', f'https://open.spotify.com/track/{track_id}'),
                            'file_path': song_info['file_path'],
                            'thumbnail': song_info.get('thumbnail'),
                            'duration': await get_audio_duration(song_info['file_path']),
                            'is_stream': song_info.get('is_stream', False),
                            'is_from_playlist': True,
                            'requester': ctx.author,
                            'ctx': ctx
                        }
                        self.queue.append(queue_entry)
                
                if not self.is_playing and not self.voice_client.is_playing():
                    await process_queue(self)

            if len(tracks) > 1:
                asyncio.create_task(self._process_spotify_tracks(
                    tracks[1:],
                    ctx,
                    status_msg,
                    f"Album: {album['name']}"
                ))

            return song_info if tracks else None

        except Exception as e:
            print(f"Error handling Spotify album: {str(e)}")
            raise

    async def handle_spotify_playlist(self, playlist_id, ctx, status_msg=None):
        """
        Handle a Spotify playlist.
        
        This method extracts all tracks from a Spotify playlist and processes them
        in the background, allowing the first track to start playing immediately.
        
        Args:
            playlist_id: The Spotify playlist ID
            ctx: Discord command context
            status_msg: Optional message to update with progress
            
        Returns:
            dict or None: Information about the first track if successful, None otherwise
        """
        try:
            playlist = self.sp.playlist(playlist_id)
            if not playlist:
                raise ValueError("Could not find playlist on Spotify")

            if status_msg:
                await status_msg.edit(embed=create_embed(
                    "Processing Playlist",
                    f"Processing playlist: {playlist['name']}\nTotal tracks: {playlist['tracks']['total']}",
                    color=0x1DB954,
                    thumbnail_url=playlist['images'][0]['url'] if playlist['images'] else None,
                    ctx=ctx
                ))
                await status_msg.delete(delay=5)

            tracks = []
            skipped_local = 0
            results = playlist['tracks']
            
            # Filter out local tracks
            for item in results['items']:
                if item['track']:
                    if item['track'].get('id') is None or item['track'].get('is_local', False):
                        skipped_local += 1
                        continue
                    tracks.extend([item])
                    
            # Get remaining pages
            while results['next']:
                results = self.sp.next(results)
                for item in results['items']:
                    if item['track']:
                        if item['track'].get('id') is None or item['track'].get('is_local', False):
                            skipped_local += 1
                            continue
                        tracks.extend([item])

            if skipped_local > 0:
                print(f"{GREEN}Playlist contains {skipped_local} local tracks. skipping...{RESET}")

            # Shuffle tracks if enabled
            if config_vars.get('DOWNLOADS', {}).get('SHUFFLE_DOWNLOAD', False):
                random.shuffle(tracks)

            if tracks:
                first_track = tracks[0]['track']
                track_id = first_track['id']
                artists = ", ".join([artist['name'] for artist in first_track['artists']])
                
                # Check cache first for the first track
                cached_info = playlist_cache.get_cached_spotify_track(track_id)
                if cached_info:
                    print(f"{GREEN}Found cached Spotify track: {track_id} - {cached_info.get('title', 'Unknown')}{RESET}")
                    
                    # Delete the "Processing" message if it exists
                    if status_msg:
                        try:
                            await status_msg.delete()
                        except discord.NotFound:
                            pass
                        except Exception as e:
                            print(f"Note: Could not delete processing message: {e}")
                    
                    first_song = {
                        'title': cached_info.get('title', 'Unknown'),
                        'url': cached_info.get('url', f'https://open.spotify.com/track/{track_id}'),
                        'file_path': cached_info['file_path'],
                        'thumbnail': cached_info.get('thumbnail'),
                        'is_from_playlist': True,
                        'requester': ctx.author,
                        'duration': await get_audio_duration(cached_info['file_path']),
                        'ctx': ctx
                    }
                    self.queue.append(first_song)
                else:
                    # Download if not in cache
                    search_query = f"{first_track['name']} {artists}"
                    first_song = await self.download_song(search_query, status_msg=None, ctx=ctx)
                    if first_song:
                        # Cache the first track
                        playlist_cache.add_spotify_track(
                            track_id,
                            first_song['file_path'],
                            title=first_song['title'],
                            thumbnail=first_song.get('thumbnail'),
                            artist=artists
                        )
                        print(f"{GREEN}Added Spotify track to cache: {track_id} - {first_song.get('title', 'Unknown')}{RESET}")
                        
                        first_song['is_from_playlist'] = True
                        first_song['requester'] = ctx.author
                        first_song['duration'] = await get_audio_duration(first_song['file_path'])
                        first_song['ctx'] = ctx
                        
                        self.queue.append(first_song)
                
                if not self.is_playing and not self.voice_client.is_playing():
                    await process_queue(self)

            if len(tracks) > 1:
                asyncio.create_task(self._process_spotify_tracks(
                    [t['track'] for t in tracks[1:]],
                    ctx,
                    status_msg,
                    f"Playlist: {playlist['name']}"
                ))

            return first_song if tracks else None

        except Exception as e:
            print(f"Error handling Spotify playlist: {str(e)}")
            raise

    async def _process_spotify_tracks(self, tracks, ctx, status_msg, source_name):
        """
        Process remaining Spotify tracks in the background.
        
        This method downloads each track in the list and adds it to the queue.
        It runs asynchronously to allow the first track to start playing immediately
        while the rest are processed in the background.
        
        Args:
            tracks: List of Spotify track objects
            ctx: Discord command context
            status_msg: Optional message to update with progress
            source_name: Name of the source (album or playlist)
        """
        try:
            total_tracks = len(tracks)
            processed = 0
            
            # First, process all cached tracks quickly
            cached_tracks = []
            uncached_tracks = []
            
            for track in tracks:
                if not track:
                    continue
                    
                track_id = track['id']
                cached_info = playlist_cache.get_cached_spotify_track(track_id)
                
                if cached_info:
                    cached_tracks.append((track_id, track, cached_info))
                else:
                    uncached_tracks.append(track)
            
            # Process all cached tracks first (faster)
            for track_id, track, cached_info in cached_tracks:
                try:
                    if not playlist_cache._should_continue_check:
                        return
                        
                    print(f"{GREEN}Found cached Spotify track: {track_id} - {cached_info.get('title', 'Unknown')}{RESET}")
                    
                    song_info = {
                        'title': cached_info.get('title', 'Unknown'),
                        'url': cached_info.get('url', f'https://open.spotify.com/track/{track_id}'),
                        'file_path': cached_info['file_path'],
                        'thumbnail': cached_info.get('thumbnail'),
                        'is_from_playlist': True,
                        'requester': ctx.author,
                        'duration': await get_audio_duration(cached_info['file_path']),
                        'ctx': ctx
                    }
                    
                    if not playlist_cache._should_continue_check:
                        return
                        
                    self.queue.append(song_info)
                    processed += 1
                except Exception as e:
                    print(f"{RED}Error processing cached track {track_id}: {str(e)}{RESET}")
                    continue
            
            # Now process uncached tracks normally
            for track in uncached_tracks:
                try:
                    if not playlist_cache._should_continue_check:
                        return
                        
                    track_id = track['id']
                    artists = ", ".join([artist['name'] for artist in track['artists']])
                    search_query = f"{track['name']} {artists}"
                    
                    song_info = await self.download_song(search_query, status_msg=None, ctx=ctx)
                    if song_info:
                        if not playlist_cache._should_continue_check:
                            return
                            
                        # Cache the downloaded song
                        playlist_cache.add_spotify_track(
                            track_id,
                            song_info['file_path'],
                            title=song_info['title'],
                            thumbnail=song_info.get('thumbnail'),
                            artist=artists
                        )
                        print(f"{GREEN}Added Spotify track to cache: {track_id} - {song_info.get('title', 'Unknown')}{RESET}")
                        
                        song_info['duration'] = await get_audio_duration(song_info['file_path'])
                        song_info['is_from_playlist'] = True
                        song_info['requester'] = ctx.author
                        song_info['ctx'] = ctx
                        
                        if not playlist_cache._should_continue_check:
                            return
                            
                        self.queue.append(song_info)
                        
                        if not self.is_playing and not self.voice_client.is_playing():
                            await process_queue(self)
                    processed += 1
                except Exception as e:
                    print(f"{RED}Error processing track {track_id}: {str(e)}{RESET}")
                    continue

        except Exception as e:
            print(f"{RED}Error in _process_spotify_tracks: {str(e)}{RESET}")