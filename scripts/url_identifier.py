import re
from urllib.parse import urlparse

def is_radio_stream(url):
    """Check if the URL is a radio stream"""
    stream_extensions = ['.mp3', '.aac', '.m4a', '.flac', '.wav', '.ogg', '.opus', '.m3u8', '.wma']
    return any(url.lower().endswith(ext) for ext in stream_extensions)

def is_playlist_url(url):
    """Check if the URL is a YouTube playlist"""
    return 'youtube.com/playlist' in url.lower()

def is_url(query):
    """Check if the query is a URL"""
    return query.startswith(('http://', 'https://', 'www.'))