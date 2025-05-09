import logging
import sys
import re
from datetime import datetime
from scripts.caching import playlist_cache
import os
from scripts.constants import GREEN, BLUE, RED, RESET

class MessageFilter(logging.Filter):
    """
    Filter out specific log messages.
    
    This class filters out unnecessary or verbose log messages to keep the log output
    clean and focused on important information. It can be configured to allow all
    messages in debug mode.
    
    Args:
        debug_mode: If True, no messages will be filtered regardless of content
    """
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
            'Shard ID None has successfully RESUMED session', # Ignore shard ID None messages
            'discord.gateway: Shard ID None has successfully RESUMED session', # Ignore shard ID None messages
            'Post-process file',          # Ignore post-processing info
            'Voice connection complete',   # Voice connection messages
            'Voice handshake complete',    # Voice connection messages
            'Connecting to voice',         # Voice connection messages
            'Starting voice handshake',    # Voice connection messages
            'ffmpeg-location ffmpeg does not exist', # Ignore false FFmpeg warning
            'writing DASH m4a',           # Ignore DASH format warning
            'should have terminated with a return code',
            'has not terminated. Waiting to terminate',
            'discord.client: Attempting a reconnect in',
            'ffmpeg process',              # Ignore FFmpeg process termination messages
            'Dispatching event',           # Filter out Discord event dispatching messages
            'The voice handshake is being terminated', # Filter voice termination messages
            'discord.client Dispatching event',  # Filter out Discord event dispatching messages
            'discord.client',
            'discord.gateway',
            'discord.gateway Keeping shard ID', # Gateway shard messages
            'discord.gateway For Shard ID', # Gateway shard messages
            'YouTube said: INFO',          # Filter YouTube info messages
            'unavailable videos are hidden', # Filter unavailable video messages
            'Incomplete data received',     # Filter incomplete data messages
            'Retrying',                    # Filter retry messages
            'Giving up after',             # Filter retry exhaustion messages
            'Traceback (most recent call last):', # Filter error tracebacks
            'File "/opt/homebrew/lib/python3.13/site-packages/yt_dlp/', # Filter yt-dlp error paths
            'return func(self, *args, **kwargs)', # Filter common traceback lines
            'ExtractorError',              # Filter extractor errors
            'process_ie_result',           # Filter processing errors
            'process_video_result',        # Filter video processing errors
            'process_info',                # Filter info processing errors
            'Error downloading song',    # Filter song download errors
            'Error downloading song: ERROR:', # Filter song download errors
            '^C',                          # Filter keyboard interrupt
            'raise_no_formats',            # Filter format errors
        ]

    def filter(self, record):
        """
        Filter log records based on logger name and message content.
        
        Args:
            record: The log record to filter
            
        Returns:
            bool: True if the record should be logged, False if it should be filtered out
        """
        # In debug mode, don't filter anything
        if self.debug_mode:
            return True
            
        # Filter out messages from specific loggers
        if record.name in self.filtered_loggers:
            return False
            
        # For other loggers, filter by message content
        return not any(keyword in record.getMessage() for keyword in self.filtered_keywords)

class OutputCapture:
    """
    Captures ALL terminal output and writes it to the log file.
    
    This class intercepts all stdout and stderr output, writes it to the
    terminal as normal, but also adds timestamps and writes it to a log file.
    It removes ANSI color codes from the log file output for better readability.
    
    Args:
        log_file: Path to the log file
        stream: The stream to capture (sys.stdout or sys.stderr)
    """
    def __init__(self, log_file, stream=None):
        self.terminal = stream or sys.stdout
        self.log_file = open(log_file, 'a', encoding='utf-8')
        
    def write(self, message):
        """
        Write the message to both terminal and log file.
        
        Args:
            message: The message to write
        """
        # Skip keyboard interrupt character
        if message.strip() == "^C":
            return
            
        # Write to terminal
        self.terminal.write(message)
        # Remove color codes and clean up the message
        clean_message = message.replace(GREEN, '').replace(BLUE, '').replace(RED, '').replace(RESET, '').strip()
        if clean_message:  # Only log non-empty messages
            # Add timestamp and write directly to file
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.log_file.write(f"{timestamp} {clean_message}\n")
            self.log_file.flush()
            
    def flush(self):
        """Flush both terminal and log file streams."""
        self.terminal.flush()
        self.log_file.flush()

class YTDLPLogger(logging.Logger):
    """
    Custom logger for yt-dlp that intercepts YouTube URLs and checks cache.
    
    This logger extends the standard logging.Logger to intercept YouTube URLs
    during the download process. When it detects a YouTube URL, it checks if
    the video is already in the cache. If found, it raises a CachedVideoFound
    exception to stop the download and use the cached file instead.
    
    Args:
        name: The name of the logger
    """
    def __init__(self, name):
        super().__init__(name)
        self.current_video_id = None
        self.url_pattern = re.compile(r'https?://(?:www\.)?youtube\.com/(?:watch\?v=|shorts/|v/|embed/|e/|attribution_link\?.*v%3D|attribution_link\?.*v=|watch\?.+v=)([a-zA-Z0-9_-]+)')
        self.search_pattern = re.compile(r'\[youtube\] Extracting URL: (https://.*)')
        
    def debug(self, msg):
        """
        Process debug messages and check for cached videos.
        
        This method intercepts debug messages containing YouTube URLs,
        extracts the video ID, and checks if the video is already in the cache.
        
        Args:
            msg: The debug message
        """
        if 'Extracting URL:' in msg:
            # Try to extract video ID from the URL
            search_match = self.search_pattern.search(msg)
            if search_match:
                url = search_match.group(1)
                match = self.url_pattern.search(url)
                if match:
                    video_id = match.group(1)
                    self.current_video_id = video_id
                    
                    # Check if video is in cache
                    cached_info = playlist_cache.get_cached_info(video_id)
                    if cached_info and os.path.exists(cached_info['file_path']):
                        # Signal to stop the download by raising a special exception
                        print(f"{GREEN}Found cached YouTube file: {RESET}{BLUE}{video_id} - {cached_info.get('title', 'Unknown')}{RESET}")
                        raise CachedVideoFound(cached_info)
        
        super().debug(msg)
    
    def warning(self, msg):
        """Process warning messages."""
        super().warning(msg)
    
    def error(self, msg):
        """Process error messages."""
        super().error(msg)

class CachedVideoFound(Exception):
    """
    Special exception to signal that a video was found in cache.
    
    This exception is raised by the YTDLPLogger when it detects that a video
    being downloaded is already in the cache. It carries the cached video
    information to be used instead of downloading the video again.
    
    Args:
        cached_info: Dictionary containing information about the cached video
    """
    def __init__(self, cached_info):
        self.cached_info = cached_info
        super().__init__("Video found in cache")

def setup_logging(log_level):
    """
    Set up logging configuration for all components.
    
    This function configures the logging system for the entire application.
    It sets up file and console handlers, applies filters to reduce noise,
    and captures all terminal output to the log file.
    
    Args:
        log_level: The logging level to use (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Import color codes and datetime
    global GREEN, BLUE, RED, RESET
    from datetime import datetime
    try:
        from bot import GREEN, BLUE, RED, RESET
    except ImportError:
        GREEN = BLUE = RED = RESET = ''
    
    # Check if we're in debug mode
    is_debug = log_level.upper() == 'DEBUG'

    # Remove any existing handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    # Create handlers
    log_file = 'log.txt'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)

    # Create formatter
    class ColoredFormatter(logging.Formatter):
        def format(self, record):
            if record.name == 'yt-dlp':
                record.name = f"{RED}yt-dlp{RESET}"
            if record.levelname == 'DEBUG':
                record.levelname = f"{GREEN}{record.levelname}{RESET}"
            if '[youtube]' in record.getMessage():
                record.msg = record.msg.replace('[youtube]', f'{RED}[youtube]{RESET}')
            if '[youtube:search]' in record.getMessage():
                record.msg = record.msg.replace('[youtube:search]', f'{BLUE}[youtube:search]{RESET}')
            if '[info]' in record.getMessage():
                record.msg = record.msg.replace('[info]', f'{BLUE}[info]{RESET}')
            if '[download]' in record.getMessage():
                record.msg = record.msg.replace('[download]', f'{BLUE}[download]{RESET}')
            if '[debug]' in record.getMessage():
                record.msg = record.msg.replace('[debug]', f'{BLUE}[debug]{RESET}')
            return super().format(record)

    formatter = ColoredFormatter('%(asctime)s %(levelname)s %(name)s %(message)s', 
                               datefmt='[%H:%M:%S]')
    
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
        'discord.voice_client',
        'discord.state',
        'discord.player',
        'discord.voice_state',
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
    
    # Capture ALL terminal output
    sys.stdout = OutputCapture(log_file, sys.stdout)
    sys.stderr = OutputCapture(log_file, sys.stderr)  # Also capture error output

def get_ytdlp_logger():
    """
    Get the yt-dlp logger for use in YTDL options.
    
    This function creates and returns a custom YTDLPLogger instance for
    use with yt-dlp. The custom logger intercepts YouTube URLs and checks
    if the videos are already in the cache.
    
    Returns:
        YTDLPLogger: A custom logger for yt-dlp
    """
    # Remove any existing yt-dlp logger
    if 'yt-dlp' in logging.Logger.manager.loggerDict:
        del logging.Logger.manager.loggerDict['yt-dlp']
    
    # Register our custom logger class
    logging.setLoggerClass(YTDLPLogger)
    logger = logging.getLogger('yt-dlp')
    logging.setLoggerClass(logging.Logger)  # Reset to default Logger class
    
    return logger
