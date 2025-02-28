import re
from urllib.parse import urlparse
import requests

def is_radio_stream(url):
    """
    Check if the URL is a radio stream.
    
    This function attempts to make a HEAD request to the URL and examines
    the Content-Type header to determine if it's an audio stream. It looks
    for content types that start with 'audio' or contain 'mpegurl'.
    
    Args:
        url: The URL to check
        
    Returns:
        bool: True if the URL appears to be a radio stream, False otherwise
    """
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        content_type = response.headers.get('Content-Type', '')
        return content_type.startswith('audio') or 'mpegurl' in content_type
    except requests.RequestException:
        return False

def is_playlist_url(url):
    """
    Check if the URL is a YouTube playlist.
    
    This function checks if the URL contains the YouTube playlist identifier.
    
    Args:
        url: The URL to check
        
    Returns:
        bool: True if the URL appears to be a YouTube playlist, False otherwise
    """
    return 'youtube.com/playlist' in url.lower()

def is_youtube_channel(url):
    """
    Check if the URL is a YouTube channel link.
    
    This function checks if the URL matches any of the common patterns
    for YouTube channel URLs, including user pages, custom URLs,
    channel IDs, and handle-based URLs.
    
    Args:
        url: The URL to check
        
    Returns:
        bool: True if the URL appears to be a YouTube channel, False otherwise
    """
    channel_patterns = [
        r'youtube\.com/user/[^/\s]+$',
        r'youtube\.com/c/[^/\s]+$',
        r'youtube\.com/channel/UC[^/\s]+$',
        r'youtube\.com/@[^/\s]+$'
    ]
    return any(re.search(pattern, url.lower()) for pattern in channel_patterns)

def is_url(query):
    """
    Check if the query is a URL.
    
    This function performs a simple check to determine if the query
    string appears to be a URL by checking if it starts with common
    URL prefixes.
    
    Args:
        query: The string to check
        
    Returns:
        bool: True if the query appears to be a URL, False otherwise
    """
    return query.startswith(('http://', 'https://', 'www.'))