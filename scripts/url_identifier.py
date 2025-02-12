import re

def is_radio_stream(url):
    """Check if the URL is a radio stream"""
    stream_extensions = ['.mp3', '.aac', '.m4a', '.flac', '.wav', '.ogg', '.opus', '.m3u8', '.wma']
    return any(url.lower().endswith(ext) for ext in stream_extensions)

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