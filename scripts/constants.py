# ANSI color codes for terminal output
RED = '\033[91m'     # Used for errors and critical messages
GREEN = '\033[92m'   # Used for success messages and confirmations
BLUE = '\033[94m'    # Used for informational messages and user actions
YELLOW = '\033[93m'  # Used for warnings and important notices
RESET = '\033[0m'    # Resets text formatting to terminal defaults

def _get_embed_colors():
    """Load embed colors from config, with fallback to defaults."""
    try:
        import json
        import os
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            colors = config.get('COLORS', {})
            return {
                'ERROR': int(colors.get('ERROR', '0xe74c3c'), 16) if isinstance(colors.get('ERROR'), str) else colors.get('ERROR', 0xe74c3c),
                'SUCCESS': int(colors.get('SUCCESS', '0x2ecc71'), 16) if isinstance(colors.get('SUCCESS'), str) else colors.get('SUCCESS', 0x2ecc71),
                'INFO': int(colors.get('INFO', '0x3498db'), 16) if isinstance(colors.get('INFO'), str) else colors.get('INFO', 0x3498db),
                'NOW_PLAYING': int(colors.get('NOW_PLAYING', '0x00ff00'), 16) if isinstance(colors.get('NOW_PLAYING'), str) else colors.get('NOW_PLAYING', 0x00ff00),
                'WARNING': int(colors.get('WARNING', '0xf1c40f'), 16) if isinstance(colors.get('WARNING'), str) else colors.get('WARNING', 0xf1c40f),
                'FINISHED': int(colors.get('FINISHED', '0x808080'), 16) if isinstance(colors.get('FINISHED'), str) else colors.get('FINISHED', 0x808080),
                'SPOTIFY': int(colors.get('SPOTIFY', '0x1DB954'), 16) if isinstance(colors.get('SPOTIFY'), str) else colors.get('SPOTIFY', 0x1DB954),
            }
    except:
        pass
    # Fallback to defaults
    return {
        'ERROR': 0xe74c3c,
        'SUCCESS': 0x2ecc71,
        'INFO': 0x3498db,
        'NOW_PLAYING': 0x00ff00,
        'WARNING': 0xf1c40f,
        'FINISHED': 0x808080,
        'SPOTIFY': 0x1DB954,
    }

_COLORS = _get_embed_colors()

# Discord embed color constants (configurable via config.json COLORS section)
EMBED_COLOR_ERROR = _COLORS['ERROR']           # Red - errors and failures
EMBED_COLOR_SUCCESS = _COLORS['SUCCESS']       # Green - success confirmations
EMBED_COLOR_INFO = _COLORS['INFO']             # Blue - informational messages, queue
EMBED_COLOR_NOW_PLAYING = _COLORS['NOW_PLAYING'] # Bright green - currently playing
EMBED_COLOR_WARNING = _COLORS['WARNING']       # Yellow - warnings
EMBED_COLOR_FINISHED = _COLORS['FINISHED']     # Gray - finished/completed
EMBED_COLOR_SPOTIFY = _COLORS['SPOTIFY']       # Spotify green

# Common error messages
ERROR_NOT_IN_VOICE = "You must be in a voice channel to use this command!"
ERROR_DIFFERENT_CHANNEL = "You must be in the same voice channel as the bot to use this command!"
ERROR_BOT_NOT_CONNECTED = "I'm not connected to a voice channel!"
ERROR_NOTHING_PLAYING = "No song is currently playing!"
ERROR_QUEUE_EMPTY = "The queue is empty!"

# Playback constants
DEFAULT_INACTIVITY_TIMEOUT = 60
DEFAULT_PLAYLIST_BATCH_SIZE = 25
DEFAULT_RETRY_COUNT = 3
DEFAULT_CONNECTION_TIMEOUT = 5