import logging
import sys

def setup_logging(log_level):
    """Set up logging configuration for all components."""
    # Create handlers
    file_handler = logging.FileHandler('log.txt', encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)

    # Configure basic logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[file_handler, console_handler]
    )

    # List of all Discord.py related loggers to configure
    discord_loggers = [
        'discord',
        'yt-dlp',
        'discord.player',
        'discord.client',
        'discord.voice_client',
        'discord.gateway',
        'discord.http',
        'discord.state',
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

    # Set log level for all Discord.py loggers
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    for logger_name in discord_loggers:
        logging.getLogger(logger_name).setLevel(log_level_value)

def get_ytdlp_logger():
    """Get the yt-dlp logger for use in YTDL options."""
    return logging.getLogger('yt-dlp')
