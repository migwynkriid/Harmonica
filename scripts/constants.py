# ANSI color codes for terminal output
RED = '\033[91m'     # Used for errors and critical messages
GREEN = '\033[92m'   # Used for success messages and confirmations
BLUE = '\033[94m'    # Used for informational messages and user actions
YELLOW = '\033[93m'  # Used for warnings and important notices
RESET = '\033[0m'    # Resets text formatting to terminal defaults

# Discord embed color constants (hex values)
EMBED_COLOR_ERROR = 0xe74c3c       # Red - errors and failures
EMBED_COLOR_SUCCESS = 0x2ecc71     # Green - success confirmations
EMBED_COLOR_INFO = 0x3498db        # Blue - informational messages, queue
EMBED_COLOR_NOW_PLAYING = 0x00ff00 # Bright green - currently playing
EMBED_COLOR_WARNING = 0xf1c40f     # Yellow - warnings
EMBED_COLOR_FINISHED = 0x808080    # Gray - finished/completed
EMBED_COLOR_SPOTIFY = 0x1DB954     # Spotify green

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