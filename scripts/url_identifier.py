import re
from urllib.parse import urlparse
import requests

def is_radio_stream(url):
    """Check if the URL is a radio stream"""
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        content_type = response.headers.get('Content-Type', '')
        return content_type.startswith('audio') or 'mpegurl' in content_type
    except requests.RequestException:
        return False

def is_playlist_url(url):
    """Check if the URL is a YouTube playlist"""
    return 'youtube.com/playlist' in url.lower()

def is_youtube_channel(url):
    """Check if the URL is a YouTube channel link"""
    channel_patterns = [
        r'youtube\.com/user/[^/\s]+$',
        r'youtube\.com/c/[^/\s]+$',
        r'youtube\.com/channel/UC[^/\s]+$',
        r'youtube\.com/@[^/\s]+$'
    ]
    return any(re.search(pattern, url.lower()) for pattern in channel_patterns)

def is_url(query):
    """Check if the query is a URL"""
    return query.startswith(('http://', 'https://', 'www.'))