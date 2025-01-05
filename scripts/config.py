import os
import json
from scripts.logging import get_ytdlp_logger
from scripts.paths import get_ytdlp_path, get_ffmpeg_path

# Get the absolute path to the cache directory
CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cache'))

def load_config():
    """Load or create the configuration file."""
    default_config = {
        "OWNER_ID": "220301180562046977",
        "PREFIX": "!",
        "LOG_LEVEL": "INFO",
        "VOICE": {
            "INACTIVITY_LEAVE": False,
            "INACTIVITY_TIMEOUT": 60,
            "AUTO_LEAVE_EMPTY": True,
            "DEFAULT_VOLUME": 100
        },
        "DOWNLOADS": {
            "AUTO_CLEAR": True
        },
        "MESSAGES": {
            "SHOW_PROGRESS_BAR": True,
            "DISCORD_UI_BUTTONS": False
        }
    }

    # Create default config if it doesn't exist
    if not os.path.exists('config.json'):
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=4)

    # Load the config
    with open('config.json', 'r') as f:
        config = json.load(f)
        
        # Create a flattened version for backward compatibility
        flattened = {
            'OWNER_ID': config.get('OWNER_ID', default_config['OWNER_ID']),
            'PREFIX': config.get('PREFIX', default_config['PREFIX']),
            'LOG_LEVEL': config.get('LOG_LEVEL', default_config['LOG_LEVEL']),
            'INACTIVITY_LEAVE': config.get('VOICE', {}).get('INACTIVITY_LEAVE', default_config['VOICE']['INACTIVITY_LEAVE']),
            'INACTIVITY_TIMEOUT': config.get('VOICE', {}).get('INACTIVITY_TIMEOUT', default_config['VOICE']['INACTIVITY_TIMEOUT']),
            'AUTO_LEAVE_EMPTY': config.get('VOICE', {}).get('AUTO_LEAVE_EMPTY', default_config['VOICE']['AUTO_LEAVE_EMPTY']),
            'DEFAULT_VOLUME': config.get('VOICE', {}).get('DEFAULT_VOLUME', default_config['VOICE']['DEFAULT_VOLUME']),
            'AUTO_CLEAR_DOWNLOADS': config.get('DOWNLOADS', {}).get('AUTO_CLEAR', default_config['DOWNLOADS']['AUTO_CLEAR']),
            'SHOW_PROGRESS_BAR': config.get('MESSAGES', {}).get('SHOW_PROGRESS_BAR', default_config['MESSAGES']['SHOW_PROGRESS_BAR'])
        }
        
        # Add the nested structure to the flattened config
        flattened['VOICE'] = config.get('VOICE', default_config['VOICE'])
        flattened['DOWNLOADS'] = config.get('DOWNLOADS', default_config['DOWNLOADS'])
        flattened['MESSAGES'] = config.get('MESSAGES', default_config['MESSAGES'])
        
        return flattened
        
# Get paths
FFMPEG_PATH = get_ffmpeg_path()
YTDLP_PATH = get_ytdlp_path()

YTDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a][abr<=96]/bestaudio[abr<=96]/bestaudio/best/bestaudio*',
    'outtmpl': '%(id)s.%(ext)s',
    'extract_audio': True,
    'concurrent_fragments': 8,
    'concurrent-downloads': 4,
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
    'http_chunk_size': 1048576,
    'cachedir': CACHE_DIR,  # Use absolute path for cache directory
    'write_download_archive': True,  # Keep track of downloaded videos
    'player_client': 'web',  # Use only web player API
    'player_skip': ['mweb', 'android', 'ios']  # Skip other player APIs
}

FFMPEG_OPTIONS = {
    'executable': FFMPEG_PATH,
    'options': '-loglevel warning -vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}