import asyncio
import discord
from discord.ext import tasks, commands
import subprocess
import os
import sys
from datetime import datetime
import pytz
import json

def create_embed(title, description, color=0x3498db):
    """
    Create a Discord embed with consistent styling.
    
    This function creates a standardized Discord embed with the provided title,
    description, and color. It automatically adds the current UTC timestamp.
    
    Args:
        title: The embed title
        description: The embed description
        color: The color of the embed (default: blue)
        
    Returns:
        discord.Embed: The created embed
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(pytz.utc)
    )
    return embed

def load_config():
    """
    Load configuration from the config.json file.
    
    This function reads and parses the bot's configuration file to access
    settings related to auto-updates and other features.
    
    Returns:
        dict: The configuration settings as a dictionary
    """
    with open('config.json', 'r') as f:
        return json.load(f)

async def check_updates(bot):
    """
    Check for and apply updates to the bot.
    
    This function checks for updates from the git repository and for package
    updates via pip. If updates are found, it notifies the bot owner and
    can automatically apply the updates based on configuration settings.
    
    The function performs the following steps:
    1. Check if auto-updates are enabled in config
    2. Check for git repository updates
    3. Check for pip package updates
    4. Apply updates if conditions are met
    5. Notify the bot owner about update status
    
    Args:
        bot: The Discord bot instance
    """
    config = load_config()
    if not config.get('AUTO_UPDATE', True):
        return

    try:
        owner = await bot.fetch_user(bot.owner_id)
    except discord.NotFound:
        print("\033[91mWarning: Could not send update notification. Owner could not be contacted.\nDo you share a server with the bot?\033[0m")
        return
    except Exception as e:
        print(f"\033[91mWarning: Could not send update notification. Error: {str(e)}\033[0m")
        return

    try:
        # First check for git updates
        current_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        # Fetch updates from remote
        subprocess.run(["git", "fetch"], check=True, capture_output=True, text=True)
        # Check if we're behind the remote
        status = subprocess.run(["git", "status", "-uno"], check=True, capture_output=True, text=True).stdout
        
        needs_restart = False
        git_updated = False
        pip_updated = False

        if "Your branch is behind" in status:
            # Only proceed with update if not in voice chat
            from bot import MusicBot
            
            # Check if any server instance is in a voice channel
            is_in_voice = False
            for guild_id, instance in MusicBot._instances.items():
                if instance.voice_client and instance.voice_client.is_connected():
                    is_in_voice = True
                    break
            
            if not is_in_voice:
                try:
                    # Pull updates
                    subprocess.run(["git", "pull"], check=True, capture_output=True, text=True)
                    new_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
                    
                    if current_commit != new_commit:
                        needs_restart = True
                        git_updated = True
                except Exception as e:
                    print(f"\033[91mWarning: Failed to pull git updates: {str(e)}\033[0m")

        # Continue with pip package updates check
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', '--dry-run', '--pre', '-r', 'requirements.txt', '--break-system-packages'],
            capture_output=True,
            text=True
        )

        if "Would install" in result.stdout:
            updates = result.stdout.split('\n')
            update_msg = '\n'.join(line for line in updates if "Would install" in line)
            
            # Check if bot is in voice chat
            from bot import MusicBot
            
            # Check if any server instance is in a voice channel
            is_in_voice = False
            for guild_id, instance in MusicBot._instances.items():
                if instance.voice_client and instance.voice_client.is_connected():
                    is_in_voice = True
                    break

            if not is_in_voice:
                try:
                    # Run actual update command
                    subprocess.run(
                        [sys.executable, '-m', 'pip', 'install', '--upgrade', '--pre', '-r', 'requirements.txt', '--break-system-packages'],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    needs_restart = True
                    pip_updated = True
                except Exception as e:
                    print(f"\033[91mWarning: Failed to auto-update: {str(e)}\033[0m")

        # Only restart if either git or pip updates were applied
        if needs_restart:
            print("\n")
            update_message = "Updates found:"
            if git_updated:
                update_message += "\n- Git repository update"
            if pip_updated:
                update_message += "\n- Python package updates"
            print(update_message)
            print("The bot will restart to apply these updates")
            # Import and call restart function
            from scripts.restart import restart_bot
            restart_bot()
    except Exception as e:
        print(f"\033[91mWarning: Error checking for updates: {str(e)}\033[0m")

@tasks.loop(hours=1)
async def update_checker(bot):
    """
    Task loop that runs the update check every hour.
    
    This function sets up a background task that periodically checks
    for updates according to the specified interval.
    
    Args:
        bot: The Discord bot instance
    """
    await check_updates(bot)

async def startup_check(bot):
    """
    Run an update check when the bot starts.
    
    This function performs an immediate update check when the bot
    first starts up, ensuring it's running the latest version.
    
    Args:
        bot: The Discord bot instance
    """
    await check_updates(bot)

def setup(bot):
    """
    Set up the update scheduler.
    
    This function is called when the module is loaded. It starts the
    periodic update checker, schedules an immediate startup check,
    and adds the UpdateScheduler cog to the bot.
    
    Args:
        bot: The Discord bot instance
    """
    update_checker.start(bot)
    bot.loop.create_task(startup_check(bot))
    bot.add_cog(UpdateScheduler(bot))