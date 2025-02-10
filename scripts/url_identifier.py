import re
import aiohttp
import asyncio
from urllib.parse import urlparse

async def async_is_radio_stream(url):
    """Check if the URL is a radio stream
    
    This function checks for:
    1. Common audio stream file extensions
    2. Common radio stream URL patterns
    3. Known radio streaming hostnames
    4. Common stream-related keywords in the URL
    5. Content-Type headers indicating audio streams
    """
    # Common audio stream file extensions
    stream_extensions = ['.mp3', '.aac', '.m4a', '.flac', '.wav', '.ogg', '.opus', '.m3u8', '.wma', '.pls', '.ram']
    
    # Audio MIME types
    audio_mime_types = [
        'audio/',  # Matches any audio type
        'application/x-mpegurl',  # M3U8 streams
        'application/vnd.apple.mpegurl',  # Another M3U8 variant
        'application/x-scpls',  # PLS playlists
        'application/pls+xml',  # PLS playlists
        'application/xspf+xml',  # XSPF playlists
        'application/octet-stream'  # Some streams use this
    ]
    
    # Check for file extensions first (quick check)
    if any(url.lower().endswith(ext) for ext in stream_extensions):
        return True
    
    # Parse the URL
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        
        # Common radio streaming hostnames
        streaming_hosts = [
            'stream', 'radio', 'live', 'streaming', 'streamserver',
            'cast', 'broadcast', 'shoutcast', 'icecast', 'azuracast',
            'channels'
        ]
        
        # Check for streaming-related keywords in hostname
        if any(host in hostname for host in streaming_hosts):
            return True
        
        # Common path patterns for radio streams
        stream_paths = [
            '/stream', '/listen', '/live', '/radio', '/play',
            '/audio', '/broadcast', '/mount', '/public', '/legacy'
        ]
        
        # Check if the path contains common stream patterns
        if any(pattern in path for pattern in stream_paths):
            return True
        
        # Check for port numbers commonly used by streaming servers
        streaming_ports = ['8000', '8080', '8010', '9000']
        if any(f':{port}' in hostname for port in streaming_ports):
            return True
        
        # If none of the above patterns match, try checking the Content-Type header
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True, timeout=5) as response:
                    content_type = response.headers.get('Content-Type', '').lower()
                    if any(mime in content_type for mime in audio_mime_types):
                        return True
                    
                    # Some streams might be detected through other headers
                    server = response.headers.get('Server', '').lower()
                    if any(host in server for host in ['icecast', 'shoutcast', 'streaming']):
                        return True
                    
                    # Check for streaming-related headers
                    for header in response.headers:
                        if 'stream' in header.lower() or 'icy-' in header.lower():
                            return True
        except Exception:
            # If the HEAD request fails, try a GET request with early termination
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as response:
                        # Read just a small portion to check if it's binary data
                        content = await response.content.read(1024)
                        content_type = response.headers.get('Content-Type', '').lower()
                        if any(mime in content_type for mime in audio_mime_types):
                            return True
                        # Check if the content looks like binary audio data
                        if content.startswith(b'ID3') or content.startswith(b'OggS'):
                            return True
            except Exception:
                pass
            
        return False
        
    except Exception:
        # If URL parsing fails, fall back to extension checking
        return any(url.lower().endswith(ext) for ext in stream_extensions)

# Keep only the async version, no sync wrapper needed
is_radio_stream = async_is_radio_stream

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