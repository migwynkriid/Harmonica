import json
import os
from pathlib import Path
from typing import Dict, Optional
import time

class PlaylistCache:
    def __init__(self):
        self.cache_dir = Path(__file__).parent.parent / '.cache'
        self.cache_file = self.cache_dir / 'filecache.json'
        self.spotify_cache_file = self.cache_dir / 'spotify_cache.json'
        self.cache_dir.mkdir(exist_ok=True)
        self._load_cache()

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
        except json.JSONDecodeError:
            self.cache = {}
            self.spotify_cache = {}
        self._cleanup_cache()

    def _save_cache(self) -> None:
        """Save the cache to disk"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
        with open(self.spotify_cache_file, 'w') as f:
            json.dump(self.spotify_cache, f, indent=2)

    def _cleanup_cache(self) -> None:
        """Remove entries for files that no longer exist or have invalid format"""
        # Clean YouTube cache
        to_remove = []
        for video_id, entry in self.cache.items():
            # Check if entry has the required format
            if not isinstance(entry, dict) or 'file_path' not in entry:
                to_remove.append(video_id)
                continue
                
            # Check if file exists
            if not os.path.exists(entry['file_path']):
                to_remove.append(video_id)
        
        for video_id in to_remove:
            del self.cache[video_id]

        # Clean Spotify cache
        to_remove = []
        for track_id, entry in self.spotify_cache.items():
            if not isinstance(entry, dict) or 'file_path' not in entry:
                to_remove.append(track_id)
                continue
            if not os.path.exists(entry['file_path']):
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.spotify_cache[track_id]
        
        if to_remove:
            self._save_cache()

    def get_cached_file(self, video_id: str) -> Optional[str]:
        """Get the cached file path for a video ID if it exists"""
        if video_id in self.cache:
            file_path = self.cache[video_id]['file_path']
            if os.path.exists(file_path):
                return file_path
            del self.cache[video_id]
            self._save_cache()
        return None

    def add_to_cache(self, video_id: str, file_path: str, **kwargs) -> None:
        """Add a file to the cache with its video ID and file path"""
        self.cache[video_id] = {
            'file_path': file_path,
            'thumbnail': kwargs.get('thumbnail_url'),
            'title': kwargs.get('title', 'Unknown'),  # Save title
            'last_accessed': time.time()
        }
        self._save_cache()

    def get_cached_info(self, video_id: str) -> Optional[Dict]:
        """Get all cached info for a video ID including file path and thumbnail"""
        if video_id in self.cache:
            self.cache[video_id]['last_accessed'] = time.time()
            self._save_cache()
            return self.cache[video_id]
        return None

    def is_video_cached(self, video_id: str) -> bool:
        """Check if a video is in the cache and its file exists"""
        return self.get_cached_file(video_id) is not None

    def get_cached_spotify_track(self, track_id: str) -> Optional[Dict]:
        """Get cached info for a Spotify track if it exists"""
        if track_id in self.spotify_cache:
            info = self.spotify_cache[track_id]
            if os.path.exists(info['file_path']):
                info['last_accessed'] = time.time()
                self._save_cache()
                return info
            del self.spotify_cache[track_id]
            self._save_cache()
        return None

    def add_spotify_track(self, track_id: str, file_path: str, **kwargs) -> None:
        """Add a Spotify track to the cache"""
        self.spotify_cache[track_id] = {
            'file_path': file_path,
            'thumbnail': kwargs.get('thumbnail'),
            'title': kwargs.get('title', 'Unknown'),
            'artist': kwargs.get('artist', 'Unknown'),
            'last_accessed': time.time()
        }
        self._save_cache()

    def is_spotify_track_cached(self, track_id: str) -> bool:
        """Check if a Spotify track is in the cache and its file exists"""
        return self.get_cached_spotify_track(track_id) is not None

# Global instance
playlist_cache = PlaylistCache()
