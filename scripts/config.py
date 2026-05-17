import json
import os
from time import sleep
from scripts.logging import get_ytdlp_logger
from scripts.paths import get_ytdlp_path, get_ffmpeg_path, get_ffprobe_path, get_cache_dir, get_root_dir
from scripts.js_runtime import get_js_runtime_config, ensure_ejs_installed
from scripts.constants import RED, GREEN, BLUE, RESET, YELLOW
import psutil
from pathlib import Path

# Get the absolute path to the cache directory
CACHE_DIR = get_cache_dir()

# Safely create cache directory and subdirectories
if os.path.exists(CACHE_DIR) and not os.path.isdir(CACHE_DIR):
    os.remove(CACHE_DIR)  # Remove if it's a file
os.makedirs(CACHE_DIR, exist_ok=True)

# Create cache subdirectories for yt-dlp
for subdir in ['youtube-sigfuncs', 'youtube-nsig']:
    cache_subdir = os.path.join(CACHE_DIR, subdir)
    if os.path.exists(cache_subdir) and not os.path.isdir(cache_subdir):
        os.remove(cache_subdir)  # Remove if it's a file
    os.makedirs(cache_subdir, exist_ok=True)

def load_config():
    """
    Load or create the configuration file.
    
    This function loads the config.json file from the root directory.
    If the file doesn't exist, it creates a new one with default values.
    It also ensures that the config has all required keys and removes deprecated ones.
    
    Note: Server-specific prefixes are stored separately in server_prefixes.json
    and can be modified using the prefix command.
    
    Returns:
        dict: A dictionary containing all configuration values
    """
    default_config = {
        "OWNER_ID": "220301180562046977",               # Owner ID
        "PREFIX": "!",                                  # Default prefix for commands (can be overridden per server)
        "LOG_LEVEL": "INFO",                            # Logging level
        "AUTO_UPDATE": True,                            # Enable/disable automatic updates
        "GITHUB_REPO": "https://github.com/migwynkriid/Harmonica",  # GitHub repository URL for updates
        "RUN_STARTUP_TESTS": False,                     # if True, run pytest health check on startup (slows down startup)
        "VOICE": {
            "INACTIVITY_LEAVE": False,                  # if True, leave voice channel when bot is inactive
            "INACTIVITY_TIMEOUT": 60,                   # in seconds
            "INACTIVITY_CHECK_INTERVAL": 60,            # How often to check for inactivity (seconds)
            "STALE_DOWNLOAD_TIMEOUT": 300,              # Timeout for stale downloads before resetting (seconds)
            "AUTO_LEAVE_EMPTY": True,                   # if True, leave voice channel when it is empty
            "DEFAULT_VOLUME": 100,                      # default volume for voice connections
            "CONNECT_TIMEOUT": 10.0,                    # Timeout for connecting to voice channel
            "DISCONNECT_TIMEOUT": 5.0,                  # Timeout for disconnecting from voice channel
        },
        "DOWNLOADS": {
            "AUTO_CLEAR": False,                        # if True, clear download directory on startup
            "MIX_PLAYLIST_LIMIT": 50,                   # Maximum number of songs to download from YouTube Mix playlists
            "SHUFFLE_DOWNLOAD": False,                  # Whether to shuffle download order in playlists
            "CONCURRENT_FRAGMENTS": 8,                  # Number of concurrent fragment downloads
            "CONCURRENT_DOWNLOADS": 4,                  # Number of concurrent file downloads
            "FRAGMENT_RETRIES": 10,                     # Number of retries for fragment downloads
            "FILE_RETRIES": 5,                          # Number of retries for file downloads
            "EXTRACTOR_RETRIES": 3,                     # Number of retries for extractor
            "SOCKET_TIMEOUT": 10,                       # Socket timeout in seconds
            "HTTP_CHUNK_SIZE": 1048576,                 # HTTP chunk size (1MB default)
            "BUFFER_SIZE": 8192,                        # Buffer size for downloads
            "MAX_WAIT_FOR_DOWNLOAD": 5,                 # Max seconds to wait for download to start
            "STALE_FLAG_TIMEOUT": 300,                  # Seconds before resetting stale download flag
        },
        "MESSAGES": {
            "SHOW_PROGRESS_BAR": True,                  # if True, show download progress bar in Discord messages
            "DISCORD_UI_BUTTONS": False,                # if True, show Discord UI buttons
            "SHOW_ACTIVITY_STATUS": True,               # if True, update bot's Discord status with current song name
            "PROGRESS_BAR_WIDTH": 20,                   # Width of progress bar in characters
            "PROGRESS_UPDATE_INTERVAL": 2,              # Seconds between progress bar updates
            "LYRICS_CHUNK_SIZE": 900,                   # Max characters per lyrics chunk for Discord
            "ERROR_DELETE_DELAY": 5,                    # Seconds before auto-deleting error messages
            "STATUS_DELETE_DELAY": 10,                  # Seconds before auto-deleting status messages
            "QUEUE_TIMEOUT": 1.0,                       # Message queue timeout
        },
        "PERMISSIONS": {
            "REQUIRES_DJ_ROLE": False,                  # if True, require a DJ role to use certain commands
        },
        "SPONSORBLOCK": False,                          # if True, enable SponsorBlock
        "SPONSORBLOCK_CATEGORIES": [                       # SponsorBlock categories to remove
            "sponsor",
            "intro",
            "outro",
            "selfpromo",
            "interaction",
            "music_offtopic"
        ],
        "UI": {
            "REACTION_TIMEOUT": 60,                     # Timeout for reaction-based selections (seconds)
            "SEARCH_TIMEOUT": 30,                       # Timeout for search selection (seconds)
            "MAX_BRANCH_OPTIONS": 9,                    # Maximum number of branch options to show
        },
        "QUEUE": {
            "PAGE_SIZE": 10,                            # Number of songs per page in queue display
            "DEFAULT_SKIP_AMOUNT": 1,                   # Default number of songs to skip
        },
        "SEARCH": {
            "RESULTS_LIMIT": 5,                         # Maximum number of search results to show
            "RANDOM_LIMIT": 5,                          # Maximum search results for random command
        },
        "PLAYBACK": {
            "TRANSITION_DELAY": 0.5,                    # Delay between songs (seconds)
            "DOWNLOAD_WAIT": 1.0,                       # Wait time for download queue
            "DEFAULT_LOOP_COUNT": 999,                  # Default loop count (effectively infinite)
            "PROGRESS_BAR_SEGMENTS": 20,                # Number of segments in now playing progress bar
        },
        "SEEK": {
            "DEFAULT_FORWARD": 10,                      # Default forward seek amount (seconds)
            "DEFAULT_REWIND": 10,                       # Default rewind seek amount (seconds)
        },
        "CONNECTION": {
            "DNS_MAX_RETRIES": 5,                       # Max retries for DNS resolution
            "DNS_RETRY_DELAY": 5,                       # Delay between DNS retries (seconds)
            "RECONNECT_RESET_TIME": 300,                # Time before resetting reconnection counter (seconds)
            "ERROR_WAIT": 5,                            # Wait time after connection error (seconds)
            "DNS_SERVERS": [                            # Alternative DNS servers for failover
                "8.8.8.8",                              # Google DNS
                "8.8.4.4",                              # Google DNS (alternative)
                "1.1.1.1",                              # Cloudflare DNS
                "1.0.0.1",                              # Cloudflare DNS (alternative)
                "9.9.9.9",                              # Quad9 DNS
                "149.112.112.112"                       # Quad9 DNS (alternative)
            ],
        },
        "UPDATE": {
            "STARTUP_DELAY": 10,                        # Delay before first update check (seconds)
            "CHECK_INTERVAL_HOURS": 1,                  # Hours between update checks
            "MAX_COMMITS_DISPLAY": 5,                   # Max commits to display in update message
            "MAX_PACKAGES_DISPLAY": 5,                  # Max packages to display in update message
        },
        "LOGGING": {
            "MAX_LOG_LINES": 1000,                      # Max lines to read from log file
            "FILE_CHUNK_SIZE": 8192,                    # Chunk size for reading log files
            "THROTTLE_INTERVAL": 10,                    # Connection message throttle interval (seconds)
        },
        "CACHE": {
            "CHUNK_SIZE": 10,                           # Number of files to process at once when importing cache
        },
        "AUDIO": {
            "MAX_BITRATE": 96,                          # Maximum audio bitrate (kbps)
            "FFMPEG_BITRATE": "96k",                    # FFmpeg audio bitrate
            "PLAYBACK_BUFFER": "128k",                  # Playback buffer size
            "RECONNECT_DELAY_MAX": 5,                   # Max reconnect delay (seconds)
        },
        "RADIO": {
            "MAX_RETRIES": 3,                           # Max retries for radio stations
            "FETCH_LIMIT": 5,                           # Number of stations to fetch per request
            "MIN_BITRATE": 64,                          # Minimum bitrate for quality stations
            "MAX_OFFSET": 1000,                         # Maximum offset for random station selection
            "FALLBACK_LIMIT": 20,                       # Stations to fetch on fallback
        },
        "COLORS": {
            "ERROR": "0xe74c3c",                        # Red - error messages
            "SUCCESS": "0x2ecc71",                      # Green - success messages
            "INFO": "0x3498db",                         # Blue - info messages
            "WARNING": "0xf1c40f",                      # Yellow - warning messages
            "NOW_PLAYING": "0x00ff00",                  # Green - now playing
            "FINISHED": "0x808080",                     # Gray - finished playing
            "SPOTIFY": "0x1DB954",                      # Spotify green
        },
        "APIS": {
            "RANDOM_WORD_URL": "https://random-words-api.kushcreates.com/api?language=en&words=1",
            "RADIO_BROWSER_URL": "https://de1.api.radio-browser.info/json/stations",
            "SPONSORBLOCK_URL": "https://sponsor.ajay.app",
            "YOUTUBE_THUMBNAIL_TEMPLATE": "https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        },
    }

    # Get absolute path to config.json in root directory
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

    # Create default config if it doesn't exist
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        print(f"\n{RED}A new config file has created using default values.{RESET}")
        sleep(1.5)
        print(f"{GREEN}Config file location: {BLUE}{config_path}{RESET}")
        print(f"{GREEN}Please edit your config file accordingly.{RESET}\n")
        sleep(1.5)

    # Load the config
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Check for missing keys and remove deprecated keys
    config_updated = False
    
    def sync_dict(current, default):
        """
        Recursively sync dictionary with default values:
        - Add missing keys
        - Remove deprecated keys
        - Keep existing values for valid keys
        
        Args:
            current: The current configuration dictionary
            default: The default configuration dictionary
            
        Returns:
            bool: True if the dictionary was updated, False otherwise
        """
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

    # Sync the config with default values
    if sync_dict(config, default_config):
        config_updated = True
        with open(config_path, 'w') as f:
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
        'MIX_PLAYLIST_LIMIT': config.get('DOWNLOADS', {}).get('MIX_PLAYLIST_LIMIT', default_config['DOWNLOADS']['MIX_PLAYLIST_LIMIT']),
        'SHUFFLE_DOWNLOAD': config.get('DOWNLOADS', {}).get('SHUFFLE_DOWNLOAD', default_config['DOWNLOADS']['SHUFFLE_DOWNLOAD']),
        'SHOW_PROGRESS_BAR': config.get('MESSAGES', {}).get('SHOW_PROGRESS_BAR', default_config['MESSAGES']['SHOW_PROGRESS_BAR']),
        'SHOW_ACTIVITY_STATUS': config.get('MESSAGES', {}).get('SHOW_ACTIVITY_STATUS', default_config['MESSAGES']['SHOW_ACTIVITY_STATUS']),
        'AUTO_UPDATE': config.get('AUTO_UPDATE', default_config['AUTO_UPDATE']),
        'SPONSORBLOCK': config.get('SPONSORBLOCK', default_config['SPONSORBLOCK']),
        'SPONSORBLOCK_CATEGORIES': config.get('SPONSORBLOCK_CATEGORIES', default_config['SPONSORBLOCK_CATEGORIES']),
    }
    
    # Add the nested structure to the flattened config
    flattened['VOICE'] = config.get('VOICE', default_config['VOICE'])
    flattened['DOWNLOADS'] = config.get('DOWNLOADS', default_config['DOWNLOADS'])
    flattened['MESSAGES'] = config.get('MESSAGES', default_config['MESSAGES'])
    flattened['PERMISSIONS'] = config.get('PERMISSIONS', default_config['PERMISSIONS'])
    flattened['AUDIO'] = config.get('AUDIO', default_config['AUDIO'])
    flattened['APIS'] = config.get('APIS', default_config['APIS'])
    return flattened
        
# Get paths to external tools
FFMPEG_PATH = get_ffmpeg_path()  # Path to ffmpeg executable
FFPROBE_PATH = get_ffprobe_path()  # Path to ffprobe executable
YTDLP_PATH = get_ytdlp_path()  # Path to yt-dlp executable

# Get path to cookies file
COOKIES_PATH = os.path.join(get_root_dir(), 'cookies.txt')  # Path to cookies file

# Check for JavaScript runtime (needed for YouTube challenge solving) - silent check
ensure_ejs_installed(verbose=False)
JS_RUNTIME_CONFIG = get_js_runtime_config(verbose=False)

# Export config variables for other modules to use
config_vars = load_config()

# Get config for volume
DEFAULT_VOLUME = config_vars.get('VOICE', {}).get('DEFAULT_VOLUME', 100)
# Convert DEFAULT_VOLUME from percentage (0-100) to float (0.0-1.0)
volume_float = DEFAULT_VOLUME / 100.0  # This makes 100% = 1.0, 75% = 0.75, 50% = 0.5, etc.

# Get download config values
_downloads_config = config_vars.get('DOWNLOADS', {})
_audio_config = config_vars.get('AUDIO', {})
_apis_config = config_vars.get('APIS', {})

# Base yt-dlp options for downloading content
BASE_YTDL_OPTIONS = {
    'format': 'bestaudio[abr<=64]/bestaudio[abr<=72]/bestaudio[abr<=80]/bestaudio[abr<=88]/bestaudio[abr<=96]/bestaudio/worst', # Try different audio bitrates, fallback to worst if all fail
    'outtmpl': '%(id)s.%(ext)s',  # Output filename template
    'extract_audio': True,  # Extract audio from video
    'concurrent_fragments': _downloads_config.get('CONCURRENT_FRAGMENTS', 8),  # Number of fragments to download concurrently
    'concurrent-downloads': _downloads_config.get('CONCURRENT_DOWNLOADS', 4),  # Number of files to download concurrently
    'fragment_retries': _downloads_config.get('FRAGMENT_RETRIES', 10),  # Number of retries for each fragment
    'retries': _downloads_config.get('FILE_RETRIES', 5),  # Number of retries for the whole file
    'abort_on_unavailable_fragments': True,  # Abort download if fragments are unavailable
    'nopostoverwrites': True,  # Do not overwrite files
    'windowsfilenames': True,  # Use Windows-compatible filenames
    'restrictfilenames': True,  # Restrict filenames to ASCII characters
    'noplaylist': True,  # Do not download playlists by default
    'quiet': False,  # Do not print messages to console
    'no_warnings': False,  # Print warnings
    'logger': get_ytdlp_logger(),  # Custom logger
    'extract_flat': False,  # Extract full info
    'force_generic_extractor': False,  # Use specific extractors when available
    'verbose': True,  # Print verbose output
    'source_address': '0.0.0.0',  # IP address to bind to
    'ffmpeg_location': FFMPEG_PATH,  # Path to ffmpeg
    'ffprobe_location': FFPROBE_PATH,  # Path to ffprobe
    'yt_dlp_filename': YTDLP_PATH,  # Path to yt-dlp
    'buffersize': _downloads_config.get('BUFFER_SIZE', 8192),  # Buffer size for downloads
    'http_chunk_size': _downloads_config.get('HTTP_CHUNK_SIZE', 1048576),  # HTTP chunk size (1MB)
    'cachedir': CACHE_DIR,  # Cache directory
    'write_download_archive': True,  # Write download archive
    'player_client': 'web',  # Pretend to be a web client
    'player_skip': ['mweb', 'android', 'ios'],  # Skip mobile clients
    'extractor_retries': _downloads_config.get('EXTRACTOR_RETRIES', 3),  # Number of retries for extractors
    'geo_bypass': True,  # Bypass geographic restrictions
    'socket_timeout': _downloads_config.get('SOCKET_TIMEOUT', 10),  # Socket timeout in seconds
    'ignore_no_formats_error': True,  # Ignore errors when no formats are available
    'ignore_unavailable_video': True,  # Ignore unavailable videos
    'cookiefile': COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,  # Path to cookies file
    'remote_components': ['ejs:github'],  # Auto-download EJS challenge solver scripts from GitHub if not found locally
}

# Add JavaScript runtime configuration if available
if JS_RUNTIME_CONFIG:
    BASE_YTDL_OPTIONS['js_runtimes'] = JS_RUNTIME_CONFIG

# Add SponsorBlock configuration if enabled in config
if config_vars.get('SPONSORBLOCK', False):
    _sponsorblock_url = _apis_config.get('SPONSORBLOCK_URL', 'https://sponsor.ajay.app')
    _sponsorblock_categories = config_vars.get('SPONSORBLOCK_CATEGORIES', ['sponsor', 'intro', 'outro', 'selfpromo', 'interaction', 'music_offtopic'])
    sponsorblock_config = {
        'sponsorblock_remove': _sponsorblock_categories,  # Types of segments to remove (from config)
        'sponsorblock_api': _sponsorblock_url,  # SponsorBlock API URL (from config)
        'postprocessors': [{
            'key': 'SponsorBlock',  # SponsorBlock postprocessor
            'when': 'before_dl',  # Apply before download
            'api': _sponsorblock_url,  # SponsorBlock API URL (from config)
            'categories': _sponsorblock_categories  # Categories to remove (from config)
        }, {
            'key': 'ModifyChapters',  # ModifyChapters postprocessor
            'remove_sponsor_segments': _sponsorblock_categories  # Segments to remove from chapters (from config)
        }]
    }
    BASE_YTDL_OPTIONS.update(sponsorblock_config)

# For backward compatibility
YTDL_OPTIONS = BASE_YTDL_OPTIONS

# FFmpeg options for audio playback
_ffmpeg_bitrate = _audio_config.get('FFMPEG_BITRATE', '96k')
_reconnect_delay = _audio_config.get('RECONNECT_DELAY_MAX', 5)
_buffer_size = _audio_config.get('PLAYBACK_BUFFER', '128k')

FFMPEG_OPTIONS = {
    'executable': FFMPEG_PATH,  # Path to ffmpeg executable
    'options': (
        f'-loglevel {config_vars["LOG_LEVEL"].lower()} -v quiet -hide_banner '  # Set logging level and reduce console output
        '-vn '  # Disable video processing completely
        f'-b:a {_ffmpeg_bitrate} '  # Set audio bitrate (from config)
        '-reconnect 1 '  # Enable reconnection if the connection is lost
        '-reconnect_streamed 1 '  # Enable reconnection for streamed content
        f'-reconnect_delay_max {_reconnect_delay} '  # Maximum delay between reconnection attempts (from config)
        f'-threads {psutil.cpu_count(logical=True)} '  # Use all available CPU threads for processing
        '-af '  # Begin audio filter chain
        'aresample=async=1:min_hard_comp=0.100000:max_soft_comp=0.100000:first_pts=0,'  # Resample audio with async mode to handle timing issues
        'equalizer=f=100:t=h:width=200:g=-3,'  # Apply high-shelf equalizer at 100Hz with -3dB gain
        f'volume={volume_float} '  # Apply volume adjustment from config
        f'-buffer_size {_buffer_size}'  # Set buffer size (from config)
    ),
}