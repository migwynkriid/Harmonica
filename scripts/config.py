import os
import json
from scripts.logging import get_ytdlp_logger
from scripts.paths import get_ytdlp_path, get_ffmpeg_path

# Get the absolute path to the cache directory
CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cache'))

# Safely create cache directory and subdirectories
if os.path.exists(CACHE_DIR) and not os.path.isdir(CACHE_DIR):
    os.remove(CACHE_DIR)  # Remove if it's a file
os.makedirs(CACHE_DIR, exist_ok=True)

for subdir in ['youtube-sigfuncs', 'youtube-nsig']:
    cache_subdir = os.path.join(CACHE_DIR, subdir)
    if os.path.exists(cache_subdir) and not os.path.isdir(cache_subdir):
        os.remove(cache_subdir)  # Remove if it's a file
    os.makedirs(cache_subdir, exist_ok=True)

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
            "DEFAULT_VOLUME": 100,
        },
        "DOWNLOADS": {
            "AUTO_CLEAR": True,
        },
        "MESSAGES": {
            "SHOW_PROGRESS_BAR": True,
            "DISCORD_UI_BUTTONS": False,
        },
        "PERMISSIONS": {
            "REQUIRES_DJ_ROLE": False,
        }
    }

    # Create default config if it doesn't exist
    if not os.path.exists('config.json'):
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=4)

    # Load the config
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Check for missing keys and remove deprecated keys
    config_updated = False
    
    def sync_dict(current, default):
        """Recursively sync dictionary with default values:
        - Add missing keys
        - Remove deprecated keys
        - Keep existing values for valid keys"""
        updated = False
        
        # Add missing keys and update nested dicts
        for key, value in default.items():
            if key not in current:
                current[key] = value
                updated = True
            elif isinstance(value, dict) and isinstance(current[key], dict):
                if sync_dict(current[key], value):
                    updated = True
        
        # Remove deprecated keys
        deprecated_keys = [k for k in current.keys() if k not in default]
        for key in deprecated_keys:
            del current[key]
            updated = True
            
        return updated

    if sync_dict(config, default_config):
        config_updated = True
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        
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
        'SHOW_PROGRESS_BAR': config.get('MESSAGES', {}).get('SHOW_PROGRESS_BAR', default_config['MESSAGES']['SHOW_PROGRESS_BAR']),
    }
    
    # Add the nested structure to the flattened config
    flattened['VOICE'] = config.get('VOICE', default_config['VOICE'])
    flattened['DOWNLOADS'] = config.get('DOWNLOADS', default_config['DOWNLOADS'])
    flattened['MESSAGES'] = config.get('MESSAGES', default_config['MESSAGES'])
    flattened['PERMISSIONS'] = config.get('PERMISSIONS', default_config['PERMISSIONS'])
    return flattened
        
# Get paths
FFMPEG_PATH = get_ffmpeg_path()
YTDLP_PATH = get_ytdlp_path()

# Get config for volume
config = load_config()
DEFAULT_VOLUME = config.get('VOICE', {}).get('DEFAULT_VOLUME', 100)
# Convert DEFAULT_VOLUME from percentage (0-100) to float (0.0-2.0)
volume_float = DEFAULT_VOLUME / 50.0  # This makes 100% = 2.0, 50% = 1.0, etc.

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
    'options': (
        f'-loglevel {config["LOG_LEVEL"].lower()} '
        '-vn '
        '-reconnect 1 '
        '-reconnect_streamed 1 '
        '-reconnect_delay_max 5 '
        '-threads 4 '
        '-af '
        'aresample=async=1:min_hard_comp=0.100000:first_pts=0,'
        'equalizer=f=100:t=h:width=200:g=-6,'
        f'volume={volume_float} '
        '-buffer_size 64k'
    ),
}