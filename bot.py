import os
import discord
import yt_dlp
import asyncio
import subprocess
import sys
import json
import signal
import socket
import aiohttp
from pathlib import Path
from datetime import datetime
from discord.ext import commands, tasks
from dotenv import load_dotenv
from scripts.commandlogger import CommandLogger
from scripts.constants import RED, GREEN, BLUE, RESET, YELLOW
from scripts.musicbot import MusicBot
from scripts.process_queue import process_queue
from scripts.clear_queue import clear_queue
from scripts.config import load_config
from scripts.logging import setup_logging
from scripts.updatescheduler import update_checker
from scripts.voice import handle_voice_state_update
from scripts.messages import create_embed
from scripts.ytdlp import get_ytdlp_path
from scripts.ffmpeg import get_ffmpeg_path
from scripts.cleardownloads import clear_downloads_folder
from scripts.load_commands import load_commands
from scripts.load_scripts import load_scripts
from scripts.activity import update_activity
from scripts.priority import set_high_priority
from scripts.paths import get_downloads_dir, get_root_dir
from scripts.server_prefixes import get_prefix, init_server_prefixes_sync
from scripts.setup import run_setup
from scripts.connection_handler import patch_discord_client

# Apply the connection handler patch to improve DNS resolution handling
patch_discord_client()

# Check if .env file exists, if not run setup
env_path = Path('.env')
if not env_path.exists():
    print(f"{YELLOW}No .env file found. Starting first-time setup...{RESET}")
    if not run_setup():
        print(f"{RED}Setup failed. Exiting...{RESET}")
        sys.exit(1)
    print(f"{GREEN}Setup completed. Starting bot...{RESET}")

# Load environment variables
load_dotenv()

# Check if Discord token is available
discord_token = os.getenv('DISCORD_TOKEN')
if not discord_token:
    print(f"{RED}Discord token not found in .env file. Please run setup again.{RESET}")
    if not run_setup():
        print(f"{RED}Setup failed. Exiting...{RESET}")
        sys.exit(1)
    # Reload environment variables after setup
    load_dotenv()
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        print(f"{RED}Discord token still not found. Exiting...{RESET}")
        sys.exit(1)
    print(f"{GREEN}Discord token successfully configured.{RESET}")

# Load configuration from config.json
config_vars = load_config()
OWNER_ID = config_vars['OWNER_ID']  # Discord user ID of the bot owner
PREFIX = config_vars['PREFIX']  # Command prefix (e.g., !)
LOG_LEVEL = config_vars['LOG_LEVEL']  # Logging verbosity level
INACTIVITY_TIMEOUT = config_vars['INACTIVITY_TIMEOUT']  # Time in seconds before bot leaves due to inactivity
AUTO_LEAVE_EMPTY = config_vars['AUTO_LEAVE_EMPTY']  # Whether to leave voice channel when empty
DEFAULT_VOLUME = config_vars['DEFAULT_VOLUME']  # Default playback volume
AUTO_CLEAR_DOWNLOADS = config_vars['AUTO_CLEAR_DOWNLOADS']  # Whether to clear downloads folder automatically
SHOW_PROGRESS_BAR = config_vars['SHOW_PROGRESS_BAR']  # Whether to show download progress bar
# Set up logging
setup_logging(LOG_LEVEL)

# Get paths to external tools
YTDLP_PATH = get_ytdlp_path()  # Path to yt-dlp executable
FFMPEG_PATH = get_ffmpeg_path()  # Path to ffmpeg executable

# Set up directories
ROOT_DIR = Path(get_root_dir())  # Root directory of the bot
DOWNLOADS_DIR = ROOT_DIR / get_downloads_dir()  # Directory for downloaded audio files

# Create downloads directory if it doesn't exist
if not DOWNLOADS_DIR.exists():
    DOWNLOADS_DIR.mkdir()

# Initialize server prefixes file synchronously before bot startup
init_server_prefixes_sync()

# Set up Discord intents (permissions)
intents = discord.Intents.default()
intents.message_content = True  # Allow bot to read message content
intents.voice_states = True  # Allow bot to track voice state changes

# Initialize the bot with configuration
bot = commands.Bot(
    command_prefix=get_prefix,  # Use dynamic prefix function
    intents=intents,
    help_command=None,  # Disable default help command
    case_insensitive=True,  # Make commands case-insensitive
    owner_id=int(OWNER_ID)  # Set bot owner
)

# Initialize command logger
command_logger = CommandLogger()

@bot.event
async def on_command(ctx):
    """Log commands when they are used"""
    command_name = ctx.command.name if ctx.command else "unknown"
    full_command = ctx.message.content
    username = str(ctx.author)
    server_name = ctx.guild.name if ctx.guild else "DM"
    command_logger.log_command(username, full_command, server_name)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    # Silently ignore CommandNotFound errors
    if isinstance(error, commands.CommandNotFound):
        return
    
    # Log the error
    print(f"Error in command {ctx.command}: {str(error)}")
    
    # Send error message to user
    await ctx.send(
        embed=create_embed(
            "Error",
            f"Error: {str(error)}",
            color=0xe74c3c,
            ctx=ctx
        )
    )

@bot.event
async def on_voice_state_update(member, before, after):
    """Event handler for voice state updates - tracks when users join/leave voice channels"""
    global music_bot
    # Get the server-specific instance of MusicBot
    if member.guild and member.guild.id:
        server_music_bot = MusicBot.get_instance(str(member.guild.id))
        await handle_voice_state_update(server_music_bot, member, before, after)

music_bot = None
first_ready = True  # Track if this is the first time the bot is ready

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord"""
    global music_bot, first_ready
    
    # Check if this is a reconnection
    is_reconnection = not first_ready
    
    if is_reconnection:        
        # Update activity status
        await update_activity(bot)
        
        # Only start the update_checker if it's not already running
        if not update_checker.is_running():
            update_checker.start(bot)
            
        return
    
    # Mark that we've completed the first ready event
    first_ready = False
    
    clear_downloads_folder()
    set_high_priority()
    prefix = config_vars.get('PREFIX', '!')  # Get prefix from config
    
    # Setup a MusicBot instance for initialization
    setup_bot = MusicBot.get_instance('setup')
    
    # Display the ASCII art logo first
    with open('scripts/consoleprint.txt', 'r') as f: print(f"{BLUE}{f.read()}{RESET}")
    commit_count = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD']).decode('utf-8').strip()
    print(f"{GREEN}\nCurrent commit count: {BLUE}{commit_count}{RESET}")
    print(f"{GREEN}YT-DLP version: {BLUE}{yt_dlp.version.__version__}{RESET}")
    print(f"----------------------------------------")
    
    # Now show the credentials
    setup_bot.show_credentials()
    MusicBot._credentials_shown = True
    
    # Continue with the rest of initialization
    await update_activity(bot)
    owner_name = f"{RED}Not found.\nOwner could not be fetched. Do you share a server with the bot?\nPlease check your config.json{RESET}"
    try:
        owner = await bot.fetch_user(OWNER_ID)
        owner_name = f"{BLUE}{owner.name}{RESET}"
    except discord.NotFound:
        pass
    except Exception as e:
        owner_name = f"{RED}Error contacting owner: {str(e)}{RESET}"

    print(f"{GREEN}Logged in as {RESET}{BLUE}{bot.user.name}")
    print(f"{GREEN}Bot ID: {RESET}{BLUE}{bot.user.id}")
    print(f"{GREEN}Bot Invite URL: {RESET}{BLUE}{discord.utils.oauth_url(bot.user.id)}{RESET}")
    print(f"----------------------------------------")
    print(f"{GREEN}Loaded configuration:{RESET}")
    print(f"{GREEN}Owner ID:{RESET} {BLUE}{OWNER_ID}{RESET} ")
    print(f"{GREEN}Owner name:{RESET} {BLUE}{owner_name}{RESET}")
    print(f"{GREEN}Command Prefix:{RESET} {BLUE}{PREFIX}{RESET} ")
    config = load_config()
    auto_update = config.get('AUTO_UPDATE', True)
    status_color = GREEN if auto_update else RED
    disabled_msg = f'Disabled. To update your instance - use {prefix}update'
    update_msg = f"{GREEN}Auto update: {BLUE if auto_update else RED}{'Enabled' if auto_update else disabled_msg}{RESET}"
    print(update_msg)
    print(f"{GREEN}SponsorBlock:{RESET} {BLUE if config.get('SPONSORBLOCK', False) else RED}{'Enabled' if config.get('SPONSORBLOCK', False) else 'Disabled'}{RESET}")
    
    # Show clear downloads status with cached files count
    auto_clear = config.get('AUTO_CLEAR_DOWNLOADS', False)
    cached_files_count = 0
    
    # Get the number of cached files from filecache.json if it exists
    filecache_path = os.path.join(ROOT_DIR, '.cache', 'filecache.json')
    if os.path.exists(filecache_path) and not auto_clear:
        try:
            with open(filecache_path, 'r') as f:
                filecache = json.load(f)
                cached_files_count = len(filecache)
        except Exception as e:
            print(f"{RED}Error reading filecache: {str(e)}{RESET}")
    
    print(f"{GREEN}Clear downloads:{RESET} {BLUE if auto_clear else RED}{'Enabled' if auto_clear else 'Disabled'}{RESET} - ", end="")
    if auto_clear:
        print(f"{YELLOW}Caching will be limited{RESET}")
    else:
        print(f"{GREEN}Caching is enabled with {BLUE}{cached_files_count}{GREEN} files currently cached{RESET}")

    # Run tests asynchronously and print a concise summary
    async def _run_tests_and_report():
        try:
            loop = asyncio.get_event_loop()
            def _worker():
                return subprocess.run(
                    [sys.executable, '-m', 'pytest', '-q', '-rA', '--disable-warnings'],
                    cwd=str(ROOT_DIR), capture_output=True, text=True
                )
            result = await loop.run_in_executor(None, _worker)
            output = (result.stdout or '') + '\n' + (result.stderr or '')

            import re as _re
            passed = 0
            failed = 0
            mp = _re.search(r"(\d+)\s+passed", output)
            mf = _re.search(r"(\d+)\s+failed", output)
            if mp:
                passed = int(mp.group(1))
            if mf:
                failed = int(mf.group(1))

            status_color = GREEN if failed == 0 else RED
            fail_color = GREEN if failed == 0 else RED
            print(f"{status_color}Running test health check:{RESET} {BLUE}{passed} passed{RESET}, {fail_color}{failed} failed{RESET}")

            if failed:
                failed_lines = [ln.strip() for ln in output.splitlines() if ln.startswith('FAILED ')]
                if failed_lines:
                    print(f"{RED}Failures:{RESET}")
                    for ln in failed_lines[:20]:
                        print(f"{RED}- {ln}{RESET}")
                else:
                    # Fallback: show tail of output for context
                    tail = '\n'.join(output.splitlines()[-50:])
                    print(f"{RED}Failure details (tail):{RESET}\n{tail}")
        except Exception as e:
            print(f"{RED}Failed to run tests:{RESET} {BLUE}{str(e)}{RESET}")

    asyncio.create_task(_run_tests_and_report())

    # Load scripts and commands
    load_scripts()
    await load_commands(bot)
    
    # Only start the update_checker if it's not already running
    if not update_checker.is_running():
        update_checker.start(bot)
    
    if not music_bot:
        music_bot = MusicBot  # Store the class, not an instance
        # Initialize the bot for setup purposes (shared resources)
        setup_instance = MusicBot.get_instance('setup')
        # Ensure the bot_loop is set to the current event loop
        setup_instance.bot_loop = asyncio.get_event_loop()
        await setup_instance.setup(bot)
        
        # Set the bot reference for all existing instances
        for guild_id, instance in MusicBot._instances.items():
            instance.bot = bot
            # Ensure each instance has the same event loop
            instance.bot_loop = setup_instance.bot_loop

bot.remove_command('help')

# Add signal handlers for immediate shutdown
def signal_handler(sig, frame):
    # Clear the current line to remove the ^C character
    print('\r', end='')
    print(f"{RED}Shutting down...{RESET}")
    # Use os._exit which exits immediately without cleanup
    os._exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@bot.event
async def on_error(event, *args, **kwargs):
    """
    Global error handler for all events.
    
    This function handles errors that occur during event processing,
    with special handling for connection-related errors.
    
    Args:
        event: The event that raised the error
        *args: Arguments passed to the event
        **kwargs: Keyword arguments passed to the event
    """
    import traceback
    from scripts.connection_handler import ConnectionHandler
    
    error_type, error, error_traceback = sys.exc_info()
    
    # Check if it's a connection-related error
    if error_type in (socket.gaierror, aiohttp.ClientConnectorError, 
                     aiohttp.ClientConnectorDNSError, discord.errors.ConnectionClosed):
        print(f"{RED}Connection error in {event}: {error}{RESET}")
        # Use our connection handler to handle the error
        handled = await ConnectionHandler.handle_connection_error(error, bot)
        if handled:
            print(f"{GREEN}Connection error handled, reconnection should succeed{RESET}")
            return
    
    # For other errors, print the traceback
    error_message = ''.join(traceback.format_exception(error_type, error, error_traceback))
    print(f"{RED}Error in {event}: {error_message}{RESET}")
    
    # Log to file
    with open('error.log', 'a') as f:
        f.write(f"[{datetime.now()}] Error in {event}:\n{error_message}\n\n")

# Start the bot with the Discord token from environment variables
bot.run(os.getenv('DISCORD_TOKEN'))