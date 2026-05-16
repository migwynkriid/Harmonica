import os
import subprocess
import sys
import discord
import yt_dlp
from pathlib import Path
from discord.ext import commands
from dotenv import load_dotenv

# Local imports - only import what's actually used
from scripts.commandlogger import CommandLogger
from scripts.constants import RED, GREEN, BLUE, RESET, YELLOW
from scripts.musicbot import MusicBot
from scripts.ui_components import NowPlayingView
from scripts.config import load_config
from scripts.logging import setup_logging
from scripts.updatescheduler import update_checker
from scripts.voice import handle_voice_state_update
from scripts.messages import create_embed
from scripts.cleardownloads import clear_downloads_folder
from scripts.load_commands import load_commands
from scripts.load_scripts import load_scripts
from scripts.activity import update_activity
from scripts.priority import set_high_priority
from scripts.paths import get_downloads_dir, get_root_dir
from scripts.ytdlp import get_ytdlp_path
from scripts.ffmpeg import get_ffmpeg_path

# Load environment variables
load_dotenv()

# Load configuration
config_vars = load_config()
OWNER_ID = config_vars['OWNER_ID']
PREFIX = config_vars['PREFIX']
LOG_LEVEL = config_vars['LOG_LEVEL']
INACTIVITY_TIMEOUT = config_vars['INACTIVITY_TIMEOUT']
AUTO_LEAVE_EMPTY = config_vars['AUTO_LEAVE_EMPTY']
DEFAULT_VOLUME = config_vars['DEFAULT_VOLUME']
AUTO_CLEAR_DOWNLOADS = config_vars['AUTO_CLEAR_DOWNLOADS']
SHOW_PROGRESS_BAR = config_vars['SHOW_PROGRESS_BAR']
# Set up logging
setup_logging(LOG_LEVEL)

YTDLP_PATH = get_ytdlp_path()
FFMPEG_PATH = get_ffmpeg_path()

ROOT_DIR = Path(get_root_dir())
DOWNLOADS_DIR = ROOT_DIR / get_downloads_dir()
OWNER_ID = OWNER_ID

if not DOWNLOADS_DIR.exists():
    DOWNLOADS_DIR.mkdir()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True,
    owner_id=int(OWNER_ID)
)

command_logger = CommandLogger()

@bot.event
async def on_command(ctx):
    """Log commands when they are used"""
    command_name = ctx.command.name if ctx.command else "unknown"
    full_command = ctx.message.content
    username = str(ctx.author)
    command_logger.log_command(username, full_command)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors globally"""
    # Ignore CommandNotFound errors silently
    if isinstance(error, commands.CommandNotFound):
        return
    
    # Log the error for debugging
    print(f"Error in command {ctx.command}: {str(error)}")
    
    # Send user-friendly error message
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
    """Event handler for voice state updates"""
    music_bot = getattr(bot, 'music_bot', None)
    if music_bot:
        await handle_voice_state_update(music_bot, member, before, after)

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    clear_downloads_folder()
    set_high_priority()
    prefix = config_vars.get('PREFIX', '!')  # Get prefix from config
    from scripts.activity import update_activity
    await update_activity(bot)
    owner_name = f"{RED}Not found.\nOwner could not be fetched. Do you share a server with the bot?\nPlease check your config.json{RESET}"
    try:
        owner = await bot.fetch_user(OWNER_ID)
        owner_name = f"{BLUE}{owner.name}{RESET}"
    except discord.NotFound:
        pass
    except Exception as e:
        owner_name = f"{RED}Error contacting owner: {str(e)}{RESET}"

    with open('scripts/consoleprint.txt', 'r') as f: print(f"{BLUE}{f.read()}{RESET}")
    commit_count = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD']).decode('utf-8').strip()
    print(f"{GREEN}\nCurrent commit count: {BLUE}{commit_count}{RESET}")
    print(f"{GREEN}YT-DLP version: {BLUE}{yt_dlp.version.__version__}{RESET}")
    print(f"----------------------------------------")
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
    prefix = config_vars['PREFIX']
    disabled_msg = f'Disabled. To update your instance - use {prefix}update'
    update_msg = f"{GREEN}Auto update: {BLUE if auto_update else RED}{'Enabled' if auto_update else disabled_msg}{RESET}"
    print(update_msg)
    print(f"{GREEN}SponsorBlock:{RESET} {BLUE if config.get('SPONSORBLOCK', False) else RED}{'Enabled' if config.get('SPONSORBLOCK', False) else 'Disabled'}{RESET}")
    print(f"{GREEN}Clear downloads:{RESET} {BLUE if config.get('AUTO_CLEAR_DOWNLOADS', False) else RED}{'Enabled' if config.get('AUTO_CLEAR_DOWNLOADS', False) else 'Disabled'}{RESET} - {YELLOW if config.get('AUTO_CLEAR_DOWNLOADS', False) else GREEN}{'Caching will be limited' if config.get('AUTO_CLEAR_DOWNLOADS', False) else 'Caching is enabled'}{RESET}")

    # Load scripts and commands
    load_scripts()
    await load_commands(bot)
    update_checker.start(bot) 
    
    # Initialize MusicBot if not already done
    if not hasattr(bot, 'music_bot') or bot.music_bot is None:
        music_bot = MusicBot()
        await music_bot.setup(bot)

bot.remove_command('help')
bot.run(os.getenv('DISCORD_TOKEN'))