import json
import os
import time
import asyncio
import re
from pathlib import Path
from typing import Dict, Optional, List
from scripts.constants import RED, GREEN, RESET
from scripts.paths import get_cache_dir, get_root_dir, get_relative_path, get_absolute_path, get_cache_file, get_downloads_dir
import yt_dlp

class PlaylistCache:
    def __init__(self):
        self.root_dir = Path(get_root_dir())
        self.cache_dir = Path(get_cache_dir())
        self.cache_file = Path(get_cache_file('filecache.json'))
        self.spotify_cache_file = Path(get_cache_file('spotify_cache.json'))
        self.blacklist_file = Path(get_cache_file('blacklist.json'))
        self.downloads_dir = Path(get_downloads_dir())
        self.cache_dir.mkdir(exist_ok=True)
        self._should_continue_check = True
        self._load_cache()
        # Run import asynchronously
        asyncio.run(self._import_uncached_files())

    def stop_cache_check(self):
        """Stop the cache checking process"""
        self._should_continue_check = False

    def resume_cache_check(self):
        """Resume the cache checking process"""
        self._should_continue_check = True

    def _load_cache(self) -> None:
        """Load the cache from disk or create a new one if it doesn't exist"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {}
            
            if self.spotify_cache_file.exists():
                with open(self.spotify_cache_file, 'r') as f:
                    self.spotify_cache = json.load(f)
            else:
                self.spotify_cache = {}

            if self.blacklist_file.exists():
                with open(self.blacklist_file, 'r') as f:
                    self.blacklist = json.load(f)
            else:
                self.blacklist = {}
        except json.JSONDecodeError:
            self.cache = {}
            self.spotify_cache = {}
            self.blacklist = {}
        self._cleanup_cache()

    def _save_cache(self) -> None:
        """Save the cache to disk"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
        with open(self.spotify_cache_file, 'w') as f:
            json.dump(self.spotify_cache, f, indent=2)
        with open(self.blacklist_file, 'w') as f:
            json.dump(self.blacklist, f, indent=2)

    def _cleanup_cache(self) -> None:
        """Remove entries for files that no longer exist or have invalid format"""
        if not self._should_continue_check:
            return

        # Clean YouTube cache
        to_remove = []
        for video_id, entry in self.cache.items():
            if not self._should_continue_check:
                return  # Exit early if stop was requested
                
            # Check if entry has the required format
            if not isinstance(entry, dict) or 'file_path' not in entry:
                to_remove.append(video_id)
                continue
                
            # Check if file exists using absolute path
            absolute_path = get_absolute_path(entry['file_path'])
            if not os.path.exists(absolute_path):
                to_remove.append(video_id)
                
        if not self._should_continue_check:
            return  # Exit before making any changes if stop was requested
                
        for video_id in to_remove:
            del self.cache[video_id]
            
        # Clean Spotify cache
        to_remove = []
        for track_id, entry in self.spotify_cache.items():
            if not self._should_continue_check:
                return  # Exit early if stop was requested
                
            if not isinstance(entry, dict) or 'file_path' not in entry:
                to_remove.append(track_id)
                continue
                
            # Check if file exists using absolute path
            absolute_path = get_absolute_path(entry['file_path'])
            if not os.path.exists(absolute_path):
                to_remove.append(track_id)
                
        if not self._should_continue_check:
            return  # Exit before making any changes if stop was requested
                
        for track_id in to_remove:
            del self.spotify_cache[track_id]
        
        if to_remove and self._should_continue_check:
            self._save_cache()

    def _is_valid_youtube_id(self, video_id: str) -> bool:
        """Check if string looks like a valid YouTube video ID."""
        return bool(re.fullmatch(r"[\w-]{11}", video_id))

    async def _get_video_info(self, video_id: str, file_path: str) -> Dict:
        """Get video info from YouTube"""
        # Get cookie file path from root directory
        cookie_file = os.path.join(get_root_dir(), 'cookies.txt')
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
            'no_warnings': True
        }
        
        # Add cookies if file exists
        if os.path.exists(cookie_file):
            ydl_opts['cookiefile'] = cookie_file
        
        try:
            # Run yt-dlp in a thread pool to not block
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            )
            
            if info and info.get('title'):
                return {
                    'id': video_id,
                    'file_path': file_path,
                    'title': info['title'],
                    'thumbnail': f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg',
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'last_accessed': time.time()
                }
        except Exception as e:
            print(f"{RED}Could not get title for {video_id}: {str(e)}{RESET}")
        
        # Return basic info if YouTube fetch fails
        return {
            'id': video_id,
            'file_path': file_path,
            'title': 'Unknown',
            'thumbnail': f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg',
            'url': f"https://www.youtube.com/watch?v={video_id}",
            'last_accessed': time.time()
        }

    async def _process_chunk(self, chunk):
        """Process a chunk of files and update cache"""
        results = await asyncio.gather(*[self._get_video_info(task['id'], task['path']) for task in chunk])
        for info in results:
            self.cache[info['id']] = info
            print(f"{GREEN}Added to cache: {info['id']} - {info['title']}{RESET}")
        self._save_cache()

    async def _import_uncached_files(self):
        """Import any files from downloads directory that aren't in the cache"""
        try:
            if not os.path.exists(self.downloads_dir):
                return

            # Collect all uncached files
            to_process = []
            for filename in os.listdir(self.downloads_dir):
                if not any(filename.endswith(ext) for ext in ['.webm', '.m4a', '.mp3', '.opus']):
                    continue

                file_path = os.path.join(self.downloads_dir, filename)
                video_id = os.path.splitext(filename)[0]

                # Skip if already in cache or not a valid YouTube ID
                if video_id in self.cache or not self._is_valid_youtube_id(video_id):
                    continue

                to_process.append({'id': video_id, 'path': file_path})

            if to_process:
                # Print consolidated message for uncached files
                file_count = len(to_process)
                print(f"{GREEN}Found {file_count} uncached {'file' if file_count == 1 else 'files'}.{RESET}")
                
                # Process in chunks of 10
                chunk_size = 10
                for i in range(0, len(to_process), chunk_size):
                    chunk = to_process[i:i + chunk_size]
                    print(f"{GREEN}Processing chunk {i//chunk_size + 1}{RESET}")
                    await self._process_chunk(chunk)
                    
        except Exception as e:
            print(f"{RED}Error importing uncached files: {str(e)}{RESET}")

    def get_cached_file(self, video_id: str) -> Optional[str]:
        """Get the cached file path for a video ID if it exists"""
        if not self._should_continue_check:
            return None
            
        if video_id in self.cache:
            relative_path = self.cache[video_id]['file_path']
            absolute_path = get_absolute_path(relative_path)
            if os.path.exists(absolute_path):
                return absolute_path
        return None

    def add_to_cache(self, video_id: str, file_path: str, **kwargs) -> None:
        """Add a file to the cache with its video ID and file path"""
        if not self._should_continue_check:
            return
            
        # Always store relative path in cache
        relative_path = get_relative_path(file_path) if os.path.isabs(file_path) else file_path
        
        cache_entry = {
            'file_path': relative_path,
            'thumbnail': kwargs.get('thumbnail_url'),
            'title': kwargs.get('title', 'Unknown'),  # Save title
            'last_accessed': time.time()
        }
        self.cache[video_id] = cache_entry
        self._save_cache()

    def get_cached_info(self, video_id: str) -> Optional[Dict]:
        """Get all cached info for a video ID including file path and thumbnail"""
        if video_id in self.cache:
            info = self.cache[video_id].copy()
            # Convert relative path to absolute only when returning
            relative_path = info['file_path']
            absolute_path = get_absolute_path(relative_path) if not os.path.isabs(relative_path) else relative_path
            if os.path.exists(absolute_path):
                info['file_path'] = absolute_path
                info['last_accessed'] = time.time()
                info['id'] = video_id  # Add video ID to the info
                self._save_cache()
                return info
        return None

    def is_video_cached(self, video_id: str) -> bool:
        """Check if a video is in the cache and its file exists"""
        return self.get_cached_file(video_id) is not None

    def get_cached_spotify_track(self, track_id: str) -> Optional[Dict]:
        """Get cached info for a Spotify track if it exists"""
        if track_id in self.spotify_cache:
            info = self.spotify_cache[track_id].copy()
            # Convert relative path to absolute
            relative_path = info['file_path']
            absolute_path = get_absolute_path(relative_path)
            if os.path.exists(absolute_path):
                info['file_path'] = absolute_path
                info['last_accessed'] = time.time()
                self._save_cache()
                return info
        return None

    def add_spotify_track(self, track_id: str, file_path: str, **kwargs) -> None:
        """Add a Spotify track to the cache"""
        if not self._should_continue_check:
            return
            
        # Store relative path in cache
        relative_path = get_relative_path(file_path)
        cache_entry = {
            'file_path': relative_path,
            'thumbnail': kwargs.get('thumbnail'),
            'title': kwargs.get('title', 'Unknown'),
            'artist': kwargs.get('artist', 'Unknown'),
            'last_accessed': time.time()
        }
        self.spotify_cache[track_id] = cache_entry
        self._save_cache()

    def is_spotify_track_cached(self, track_id: str) -> bool:
        """Check if a Spotify track is in the cache and its file exists"""
        return self.get_cached_spotify_track(track_id) is not None

    def add_to_blacklist(self, video_id: str) -> None:
        """Add a video ID to the blacklist with timestamp"""
        self.blacklist[video_id] = {
            'timestamp': time.time(),
            'reason': 'Video unavailable'
        }
        self._save_cache()

    def is_blacklisted(self, video_id: str) -> bool:
        """Check if a video ID is in the blacklist"""
        return video_id in self.blacklist

# Global instance
playlist_cache = PlaylistCache()
