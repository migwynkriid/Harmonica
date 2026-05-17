import os
from pathlib import Path
import shutil

# Check if .spotifyenv exists, if not create it from example
spotifyenv_path = Path(__file__).parent.parent / '.spotifyenv'
spotifyenv_example_path = Path(__file__).parent.parent / '.spotifyenv.example'
if not spotifyenv_path.exists() and spotifyenv_example_path.exists():
    shutil.copy2(spotifyenv_example_path, spotifyenv_path)

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Load environment variables from .spotifyenv
load_dotenv('.spotifyenv')

# Lazy-initialized Spotify client
_sp = None
_sp_init_attempted = False


def _get_spotify_client():
    """Get Spotify client with lazy initialization and error handling."""
    global _sp, _sp_init_attempted
    if _sp is not None:
        return _sp
    if _sp_init_attempted:
        return None  # Already failed, don't retry
    _sp_init_attempted = True
    try:
        client_id = os.getenv('SPOTIPY_CLIENT_ID')
        client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        if not client_id or not client_secret:
            print("Warning: Spotify credentials not configured. Spotify features will be disabled.")
            return None
        _sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        ))
        return _sp
    except Exception as e:
        print(f"Warning: Failed to initialize Spotify client: {e}")
        return None


# Property-like accessor for backward compatibility
@property
def sp():
    return _get_spotify_client()


async def get_spotify_track_details(spotify_url):
    try:
        client = _get_spotify_client()
        if client is None:
            return None, None
        if 'track/' in spotify_url:
            track_id = spotify_url.split('track/')[-1].split('?')[0]
            track_info = client.track(track_id)
            artist_name = track_info['artists'][0]['name']
            track_name = track_info['name']
            return f"{artist_name} - {track_name}", track_id
    except Exception as e:
        print(f"Error retrieving Spotify track details: {str(e)}")
        return None, None

async def get_spotify_album_details(spotify_url):
    try:
        client = _get_spotify_client()
        if client is None:
            return []
        if 'album/' in spotify_url:
            album_id = spotify_url.split('album/')[-1].split('?')[0]
            album_info = client.album_tracks(album_id)
            tracks = [f"{track['artists'][0]['name']} - {track['name']}" for track in album_info['items']]
            return tracks
    except Exception as e:
        print(f"Error retrieving Spotify album details: {str(e)}")
        return []

async def get_spotify_playlist_details(spotify_url):
    try:
        client = _get_spotify_client()
        if client is None:
            return []
        if 'playlist/' in spotify_url:
            playlist_id = spotify_url.split('playlist/')[-1].split('?')[0]
            playlist_info = client.playlist_tracks(playlist_id)
            tracks = [f"{track['track']['artists'][0]['name']} - {track['track']['name']}" for track in playlist_info['items']]
            return tracks
    except Exception as e:
        print(f"Error retrieving Spotify playlist details: {str(e)}")
        return []
