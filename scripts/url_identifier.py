import re
import asyncio
import aiohttp
from urllib.parse import urlparse

async def is_radio_stream(url):
    """Check if the URL is a radio stream (async version)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=5)) as response:
                content_type = response.headers.get('Content-Type', '')
                return content_type.startswith('audio') or 'mpegurl' in content_type
    except (aiohttp.ClientError, asyncio.TimeoutError):
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