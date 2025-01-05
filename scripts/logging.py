import logging
import sys

class MessageFilter(logging.Filter):
    """Filter out specific log messages"""
    def __init__(self, debug_mode=False):
        super().__init__()
        self.debug_mode = debug_mode
        # Loggers to completely filter out
        self.filtered_loggers = {
            'discord.voice_state',    # Voice connection state changes
            'discord.gateway',        # Gateway connection messages
            'discord.player',         # FFmpeg process messages
        }
        
        # Messages to filter from other loggers
        self.filtered_keywords = [
            'Ignoring exception in view',  # Ignore button interaction timeouts
            'Downloading webpage',         # Ignore yt-dlp download info
            'Downloading video',          # Ignore yt-dlp download info
            'Extracting URL',             # Ignore yt-dlp extraction info
            'Finished downloading',       # Ignore yt-dlp finish info
            'Deleting original file',     # Ignore yt-dlp cleanup info
            'Running FFmpeg',             # Ignore FFmpeg processing info
            'Post-process file',          # Ignore post-processing info
            'Voice connection complete',   # Voice connection messages
            'Voice handshake complete',    # Voice connection messages
            'Connecting to voice',         # Voice connection messages
            'Starting voice handshake',    # Voice connection messages
            'ffmpeg-location ffmpeg does not exist', # Ignore false FFmpeg warning
            'writing DASH m4a',           # Ignore DASH format warning
            'should have terminated with a return code',
            'has not terminated. Waiting to terminate',
            'ffmpeg process',              # Ignore FFmpeg process termination messages
            'Dispatching event',           # Filter out Discord event dispatching messages
            'The voice handshake is being terminated'  # Filter voice termination messages
        ]

    def filter(self, record):
        # In debug mode, don't filter anything
        if self.debug_mode:
            return True
            
        # Filter out messages from specific loggers
        if record.name in self.filtered_loggers:
            return False
            
        # For other loggers, filter by message content
        return not any(keyword in record.getMessage() for keyword in self.filtered_keywords)

def setup_logging(log_level):
    """Set up logging configuration for all components."""
    # Check if we're in debug mode
    is_debug = log_level.upper() == 'DEBUG'

    # Remove any existing handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    # Create handlers
    file_handler = logging.FileHandler('log.txt', encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s', 
                                datefmt='%Y-%m-%d %H:%M:%S')
    
    # Add formatter to handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Create message filter with debug mode setting
    message_filter = MessageFilter(debug_mode=is_debug)

    # Set log level
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    root.setLevel(log_level_value)

    # Configure specific loggers that need to be filtered
    filtered_loggers = [
        'discord',
        'yt-dlp',
        'discord.client',
        'discord.voice_client',
        'discord.state',
        'discord.player',
        'discord.voice_state',
        'discord.gateway',
        'discord.interactions',
        'discord.webhook',
        'discord.ext.commands',
        'discord.ext.tasks',
        'discord.ext.voice_client',
        'discord.ext.commands.bot',
        'discord.ext.commands.core',
        'discord.ext.commands.errors',
        'discord.ext.commands.cog',
        'discord.ext.tasks.loop',
        'discord.ext',
        'discord.utils',
        'discord.intents'
    ]

    # Set up each Discord logger with the filter
    for logger_name in filtered_loggers:
        logger = logging.getLogger(logger_name)
        # Only apply filter if not in debug mode
        if not is_debug:
            logger.addFilter(message_filter)
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.setLevel(log_level_value)
        logger.propagate = False  # Prevent duplicate logging

    # Add handlers to root logger for non-Discord logs
    root.addHandler(file_handler)
    root.addHandler(console_handler)

def get_ytdlp_logger():
    """Get the yt-dlp logger for use in YTDL options."""
    return logging.getLogger('yt-dlp')
