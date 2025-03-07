import os
import json
import sys
import getpass
import re
import time
from pathlib import Path
from scripts.constants import RED, GREEN, BLUE, RESET, YELLOW

# Add more color constants for a richer visual experience
CYAN = '\033[96m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
DIM = '\033[2m'
BLINK = '\033[5m'

def is_valid_discord_token(token):
    """
    Validate the format of a Discord token.
    
    Args:
        token (str): The Discord token to validate
    
    Returns:
        bool: True if the token format is valid, False otherwise
    """
    # Discord tokens are typically in the format: 
    # - Bot tokens: starts with "Bot " or just the token itself
    # - User tokens: starts with "mfa." for 2FA accounts or just a string of characters
    
    # Remove "Bot " prefix if present
    if token.startswith("Bot "):
        token = token[4:]
    
    # Basic format check (not foolproof but catches obvious issues)
    # Most tokens are around 59-72 characters and contain letters, numbers, dots, and underscores
    token_pattern = re.compile(r'^[A-Za-z0-9._-]{50,100}$')
    return bool(token_pattern.match(token))

def create_env_file(discord_token):
    """
    Create a .env file with the provided Discord token.
    
    Args:
        discord_token (str): The Discord bot token
    
    Returns:
        bool: True if the file was created successfully, False otherwise
    """
    try:
        with open('.env', 'w') as f:
            f.write(f"DISCORD_TOKEN={discord_token}\n")
        return True
    except Exception as e:
        print(f"{RED}Error creating .env file: {str(e)}{RESET}")
        return False

def update_config_file(config_data):
    """
    Update the config.json file with the provided data.
    
    Args:
        config_data (dict): The configuration data to write
    
    Returns:
        bool: True if the file was updated successfully, False otherwise
    """
    try:
        # Get absolute path to config.json in root directory
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        
        # Load existing config if it exists
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                existing_config = json.load(f)
            
            # Update existing config with new values
            for key, value in config_data.items():
                if isinstance(value, dict) and key in existing_config and isinstance(existing_config[key], dict):
                    # For nested dictionaries, update values individually
                    for subkey, subvalue in value.items():
                        existing_config[key][subkey] = subvalue
                else:
                    # For top-level keys or complete replacement of nested dicts
                    existing_config[key] = value
            
            config_to_write = existing_config
        else:
            config_to_write = config_data
        
        # Write the updated config
        with open(config_path, 'w') as f:
            json.dump(config_to_write, f, indent=4)
        
        return True
    except Exception as e:
        print(f"{RED}Error updating config.json: {str(e)}{RESET}")
        return False

def get_input(prompt, default=None, password=False):
    """
    Get user input with a prompt and optional default value.
    
    Args:
        prompt (str): The prompt to display
        default (str, optional): Default value if user enters nothing
        password (bool, optional): Whether to hide input (for passwords)
    
    Returns:
        str: The user input or default value
    """
    if default:
        prompt = f"{CYAN}{prompt}{RESET} {DIM}[{default}]{RESET}: "
    else:
        prompt = f"{CYAN}{prompt}{RESET}: "
    
    if password:
        value = getpass.getpass(prompt)
    else:
        value = input(prompt)
    
    return value if value else default

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the setup header."""
    clear_screen()
    print(f"{BLUE}╔════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BLUE}║                {BOLD}{MAGENTA}Harmonica - First Time Setup{RESET}{BLUE}                ║{RESET}")
    print(f"{BLUE}╚════════════════════════════════════════════════════════════╝{RESET}")
    print()

def print_section_header(title, step_number=None):
    """Print a section header with a title."""
    if step_number:
        print(f"\n{BLUE}┌─────────────────────────────────────────────────────────────┐{RESET}")
        print(f"{BLUE}│ {BOLD}{MAGENTA}Step {step_number}: {title}{RESET}{BLUE} {' ' * (52 - len(title) - len(str(step_number)))}│{RESET}")
        print(f"{BLUE}└─────────────────────────────────────────────────────────────┘{RESET}")
    else:
        print(f"\n{BLUE}┌─────────────────────────────────────────────────────────────┐{RESET}")
        print(f"{BLUE}│ {BOLD}{MAGENTA}{title}{RESET}{BLUE} {' ' * (58 - len(title))}│{RESET}")
        print(f"{BLUE}└─────────────────────────────────────────────────────────────┘{RESET}")

def print_success(message):
    """Print a success message."""
    print(f"\n{GREEN}✓ {message}{RESET}")

def print_error(message):
    """Print an error message."""
    print(f"\n{RED}✗ {message}{RESET}")

def print_warning(message):
    """Print a warning message."""
    print(f"\n{YELLOW}⚠ {message}{RESET}")

def print_info(message):
    """Print an info message."""
    print(f"{CYAN}ℹ {message}{RESET}")

def print_tip(message):
    """Print a tip message."""
    print(f"{MAGENTA}💡 {message}{RESET}")

def animate_loading(message, duration=1.0):
    """Show an animated loading message."""
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    end_time = time.time() + duration
    i = 0
    try:
        while time.time() < end_time:
            sys.stdout.write(f"\r{CYAN}{chars[i % len(chars)]} {message}...{RESET}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        sys.stdout.write(f"\r{' ' * (len(message) + 10)}\r")
        sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stdout.write(f"\r{' ' * (len(message) + 10)}\r")
        sys.stdout.flush()

def is_valid_discord_id(user_id):
    """
    Validate the format of a Discord user ID.
    
    Args:
        user_id (str): The Discord user ID to validate
    
    Returns:
        bool: True if the ID format is valid, False otherwise
    """
    # Discord IDs are snowflakes - numeric values between 17-20 digits
    id_pattern = re.compile(r'^\d{17,20}$')
    return bool(id_pattern.match(user_id))

def run_setup():
    """
    Run the first-time setup process.
    
    This function guides the user through setting up the bot by:
    1. Getting the Discord bot token
    2. Setting the bot owner ID
    3. Configuring other bot settings
    
    Returns:
        bool: True if setup was completed successfully, False otherwise
    """
    print_header()
    print(f"{BOLD}{GREEN}Welcome to the Discord Music Bot Setup!{RESET}")
    print(f"{YELLOW}This wizard will help you configure your bot for first-time use.{RESET}")
    print()
    print(f"{CYAN}We'll guide you through setting up:{RESET}")
    print(f"{MAGENTA}  • Discord Bot Token{RESET}")
    print(f"{MAGENTA}  • Bot Owner ID{RESET}")
    print(f"{MAGENTA}  • Command Prefix{RESET}")
    print(f"{MAGENTA}  • Voice Settings{RESET}")
    print(f"{MAGENTA}  • Download Settings{RESET}")
    print(f"{MAGENTA}  • Message Settings{RESET}")
    print(f"{MAGENTA}  • Other Settings{RESET}")
    print()
    print(f"{YELLOW}Press Enter to continue...{RESET}")
    input()
    
    # Step 1: Discord Bot Token
    print_section_header("Discord Bot Token", 1)
    print_info("You need a Discord bot token to use this bot.")
    print_tip("If you don't have one, create a bot at: https://discord.com/developers/applications")
    print()
    
    discord_token = get_input("Enter your Discord bot token")
    while not discord_token or not is_valid_discord_token(discord_token):
        if not discord_token:
            print_error("Discord token is required to continue.")
        else:
            print_error("The token format appears to be invalid. Please check your token and try again.")
            print_warning("A valid Discord bot token is typically around 59-72 characters long.")
        discord_token = get_input("Enter your Discord bot token")
    
    # Create .env file with the token
    animate_loading("Saving token", 1.0)
    if not create_env_file(discord_token):
        print_error("Failed to create .env file. Setup aborted.")
        return False
    
    print_success("Discord token saved successfully!")
    
    # Step 2: Bot Owner ID
    print_section_header("Bot Owner ID", 2)
    print_info("The owner ID is your Discord user ID. The owner has special permissions.")
    print_tip("To get your ID, enable Developer Mode in Discord settings,")
    print_tip("then right-click your username and select 'Copy ID'.")
    print()
    
    owner_id = get_input("Enter your Discord user ID")
    while not owner_id or not is_valid_discord_id(owner_id):
        if not owner_id:
            print_error("Owner ID is required to continue.")
        else:
            print_error("The ID format appears to be invalid. Discord IDs are 17-20 digit numbers.")
            print_warning("Make sure you have Developer Mode enabled in Discord settings.")
        owner_id = get_input("Enter your Discord user ID")
    
    # Step 3: Command Prefix
    print_section_header("Command Prefix", 3)
    print_info("The prefix is used before commands (e.g., !play, ?play, .play)")
    
    prefix = get_input("Enter command prefix", default="!")
    
    # Step 4: Voice Settings
    print_section_header("Voice Settings", 4)
    
    inactivity_leave = get_input("Leave voice channel when inactive? (yes/no)", default="no").lower() in ['yes', 'y', 'true']
    inactivity_timeout = get_input("Inactivity timeout in seconds", default="60")
    try:
        inactivity_timeout = int(inactivity_timeout)
    except ValueError:
        inactivity_timeout = 60
        print_warning("Invalid timeout value. Using default: 60 seconds")
    
    auto_leave_empty = get_input("Leave voice channel when empty? (yes/no)", default="yes").lower() in ['yes', 'y', 'true']
    
    default_volume = get_input("Default volume (0-100)", default="100")
    try:
        default_volume = int(default_volume)
        if default_volume < 0 or default_volume > 100:
            default_volume = 100
            print_warning("Volume must be between 0-100. Using default: 100")
    except ValueError:
        default_volume = 100
        print_warning("Invalid volume value. Using default: 100")
    
    # Step 5: Download Settings
    print_section_header("Download Settings", 5)
    
    print_section_header("Caching Information")
    print_info("The bot automatically caches every download to improve response time and reduce bandwidth usage.")
    print_warning("If you enable 'Automatically clear downloads folder', caching will be limited.")
    print_success("If you disable it, full caching will be available, improving performance for repeated songs.")
    print()
    
    auto_clear = get_input("Automatically clear downloads folder? (yes/no)", default="no").lower() in ['yes', 'y', 'true']
    if auto_clear:
        print_warning("With auto-clear enabled, caching will be limited. The bot may need to re-download songs you've played before.")
    else:
        print_success("Full caching enabled. The bot will reuse downloaded songs, improving performance.")
    
    # Set mix_playlist_limit to default value without prompting
    mix_playlist_limit = 50
    
    shuffle_download = get_input("Shuffle download order in playlists? (yes/no)", default="no").lower() in ['yes', 'y', 'true']
    
    # Step 6: Message Settings
    print_section_header("Message Settings", 6)
    
    show_progress_bar = get_input("Show download progress bar? (yes/no)", default="yes").lower() in ['yes', 'y', 'true']
    discord_ui_buttons = get_input("Use Discord UI buttons? (yes/no)", default="no").lower() in ['yes', 'y', 'true']
    show_activity_status = get_input("Show current song in bot status? (yes/no)", default="yes").lower() in ['yes', 'y', 'true']
    
    # Step 7: Other Settings
    print_section_header("Other Settings", 7)
    
    auto_update = get_input("Enable automatic updates? (yes/no)", default="yes").lower() in ['yes', 'y', 'true']
    sponsorblock = get_input("Enable SponsorBlock to skip ads in videos? (yes/no)", default="no").lower() in ['yes', 'y', 'true']
    requires_dj_role = get_input("Require DJ role for music commands? (yes/no)", default="no").lower() in ['yes', 'y', 'true']
    
    # Create config dictionary
    config = {
        "OWNER_ID": owner_id,
        "PREFIX": prefix,
        "LOG_LEVEL": "INFO",
        "AUTO_UPDATE": auto_update,
        "VOICE": {
            "INACTIVITY_LEAVE": inactivity_leave,
            "INACTIVITY_TIMEOUT": inactivity_timeout,
            "AUTO_LEAVE_EMPTY": auto_leave_empty,
            "DEFAULT_VOLUME": default_volume
        },
        "DOWNLOADS": {
            "AUTO_CLEAR": auto_clear,
            "MIX_PLAYLIST_LIMIT": mix_playlist_limit,
            "SHUFFLE_DOWNLOAD": shuffle_download
        },
        "MESSAGES": {
            "SHOW_PROGRESS_BAR": show_progress_bar,
            "DISCORD_UI_BUTTONS": discord_ui_buttons,
            "SHOW_ACTIVITY_STATUS": show_activity_status
        },
        "PERMISSIONS": {
            "REQUIRES_DJ_ROLE": requires_dj_role
        },
        "SPONSORBLOCK": sponsorblock
    }
    
    # Update config.json
    animate_loading("Saving configuration", 1.5)
    if not update_config_file(config):
        print_error("Failed to update config.json. Setup aborted.")
        return False
    
    print()
    print(f"{BLUE}╔══════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BLUE}║                {BOLD}{GREEN}Setup Completed Successfully!{RESET}{BLUE}                      ║{RESET}")
    print(f"{BLUE}╚══════════════════════════════════════════════════════════════════════════╝{RESET}")
    print()
    print_success("Your bot is now configured and ready to use.")
    print_info("The bot will now start with your configuration.")
    print()
    
    return True

if __name__ == "__main__":
    # This allows the setup to be run directly
    run_setup() 