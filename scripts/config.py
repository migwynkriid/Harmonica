import os
import json
from scripts.logging import get_ytdlp_logger
from scripts.paths import get_ytdlp_path, get_ffmpeg_path

def load_config():
    """Load or create the configuration file."""
    default_config = {
        "OWNER_ID": "YOUR_DISCORD_USER_ID",
        "PREFIX": "!",
        "LOG_LEVEL": "INFO",
        "VOICE": {
            "INACTIVITY_TIMEOUT": 60,
            "AUTO_LEAVE_EMPTY": True,
            "DEFAULT_VOLUME": 100
        },
        "DOWNLOADS": {
            "AUTO_CLEAR": True
        },
        "MESSAGES": {
            "SHOW_PROGRESS_BAR": True
        }
    }

    # Create default config if it doesn't exist
    if not os.path.exists('config.json'):
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=4)

    # Load the config
    with open('config.json', 'r') as f:
        config = json.load(f)
        return {
            'OWNER_ID': config['OWNER_ID'],
            'PREFIX': config['PREFIX'],
            'LOG_LEVEL': config.get('LOG_LEVEL', 'INFO'),
            'INACTIVITY_TIMEOUT': config.get('VOICE', {}).get('INACTIVITY_TIMEOUT', 60),
            'AUTO_LEAVE_EMPTY': config.get('VOICE', {}).get('AUTO_LEAVE_EMPTY', True),
            'DEFAULT_VOLUME': config.get('VOICE', {}).get('DEFAULT_VOLUME', 100),
            'AUTO_CLEAR_DOWNLOADS': config.get('DOWNLOADS', {}).get('AUTO_CLEAR', True),
            'SHOW_PROGRESS_BAR': config.get('MESSAGES', {}).get('SHOW_PROGRESS_BAR', True)
        }
        
# Get paths
FFMPEG_PATH = get_ffmpeg_path()
YTDLP_PATH = get_ytdlp_path()

YTDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a][abr<=96]/bestaudio[abr<=96]/bestaudio/best/bestaudio*',
    'outtmpl': '%(id)s.%(ext)s',
    'extract_audio': True,
    'concurrent_fragments': 8,
    'fragment_retries': 10,
    'retries': 5,
    'abort_on_unavailable_fragments': True,
    'nopostoverwrites': True,
    'windowsfilenames': True,
    'restrictfilenames': True,
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'logger': get_ytdlp_logger(),
    'extract_flat': False,
    'force_generic_extractor': False,
    'verbose': True,
    'source_address': '0.0.0.0',
    'ffmpeg_location': FFMPEG_PATH,
    'yt_dlp_filename': YTDLP_PATH,
    'buffersize': 8192,
    'http_chunk_size': 1048576
}

FFMPEG_OPTIONS = {
    'executable': FFMPEG_PATH,
    'options': '-loglevel warning -vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}