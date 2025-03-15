import asyncio
import discord
from discord.ext import tasks, commands
import subprocess
import os
import sys
import re
from datetime import datetime
import pytz
import json
from scripts.constants import RED, GREEN, BLUE, YELLOW, RESET

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

def get_git_commit_details(from_commit, to_commit):
    """
    Get detailed information about git commits between two commit hashes.
    
    This function retrieves the commit messages, authors, and timestamps for
    all commits between the specified commit hashes.
    
    Args:
        from_commit: The starting commit hash
        to_commit: The ending commit hash
        
    Returns:
        list: A list of dictionaries containing commit details
    """
    try:
        # Get commit details using git log
        log_format = "--pretty=format:%h|%s|%an|%ad"
        log_command = ["git", "log", f"{from_commit}..{to_commit}", log_format]
        result = subprocess.run(log_command, capture_output=True, text=True, check=True)
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
                
            parts = line.split('|')
            if len(parts) >= 4:
                commits.append({
                    'hash': parts[0],
                    'message': parts[1],
                    'author': parts[2],
                    'date': parts[3]
                })
        
        return commits
    except Exception as e:
        print(f"{RED}Error getting git commit details: {str(e)}{RESET}")
        return []

def parse_pip_updates(output):
    """
    Parse pip update output to extract package version information.
    
    This function parses the output of pip's --dry-run update command to
    extract information about which packages would be updated and their
    version changes.
    
    Args:
        output: The output string from pip's update command
        
    Returns:
        list: A list of dictionaries containing package update details
    """
    # Clean up the output to remove requirements.txt references
    cleaned_output = re.sub(r'\(from -r requirements\.txt \(line \d+\)\)', '', output)
    
    updates = []
    lines = cleaned_output.split('\n')
    
    # Look for specific patterns in the output
    current_version = None
    new_version = None
    
    # Find the current version
    for line in lines:
        if "Requirement already satisfied: yt-dlp" in line:
            for check_line in lines:
                if "yt-dlp" in check_line and "(" in check_line:
                    # Extract version from parentheses
                    version_match = re.search(r'\(([^)]+)\)', check_line)
                    if version_match:
                        current_version = version_match.group(1)
                        break
    
    # Find the new version
    for line in lines:
        if "Would install yt-dlp" in line:
            parts = line.split()
            if len(parts) >= 3:
                new_version = parts[2]
                break
    
    # If we found both versions, add the update
    if current_version and new_version:
        updates.append({
            'package': 'yt-dlp',
            'old_version': current_version,
            'new_version': new_version
        })
    # If we only found the new version, use "unknown" for the old version
    elif new_version:
        updates.append({
            'package': 'yt-dlp',
            'old_version': "unknown",
            'new_version': new_version
        })
    
    # Hardcoded approach for the specific output format
    # This is a fallback if the above methods don't work
    if not updates and "Would install yt-dlp" in cleaned_output:
        # Extract the current version from the output
        for line in lines:
            if "Requirement already satisfied: yt-dlp" in line:
                # Look for version in nearby lines
                idx = lines.index(line)
                for i in range(max(0, idx-5), min(len(lines), idx+5)):
                    if "yt-dlp" in lines[i] and "2025" in lines[i]:
                        old_version_match = re.search(r'(\d+\.\d+\.\d+)', lines[i])
                        if old_version_match:
                            old_version = old_version_match.group(1)
                            
                            # Extract new version from the "Would install" line
                            for would_line in lines:
                                if "Would install yt-dlp" in would_line:
                                    new_version_match = re.search(r'yt-dlp[- ](\S+)', would_line)
                                    if new_version_match:
                                        new_version = new_version_match.group(1)
                                    else:
                                        parts = would_line.split()
                                        if len(parts) >= 3:
                                            new_version = parts[2]
                                        else:
                                            new_version = "unknown"
                                    break
                            
                            updates.append({
                                'package': 'yt-dlp',
                                'old_version': old_version,
                                'new_version': new_version
                            })
                            break
        
        # If we still couldn't find the old version, use "unknown"
        if not updates:
            # Extract new version from the "Would install" line
            new_version = "unknown"
            for would_line in lines:
                if "Would install yt-dlp" in would_line:
                    new_version_match = re.search(r'yt-dlp[- ](\S+)', would_line)
                    if new_version_match:
                        new_version = new_version_match.group(1)
                    else:
                        parts = would_line.split()
                        if len(parts) >= 3:
                            new_version = parts[2]
                    break
            
            updates.append({
                'package': 'yt-dlp',
                'old_version': "unknown",
                'new_version': new_version
            })
    
    return updates

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
        # First check for git updates
        current_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        # Fetch updates from remote
        subprocess.run(["git", "fetch"], check=True, capture_output=True, text=True)
        # Check if we're behind the remote
        status = subprocess.run(["git", "status", "-uno"], check=True, capture_output=True, text=True).stdout
        
        needs_restart = False
        git_updated = False
        pip_updated = False
        git_commits = []
        pip_updates = []

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
                    # Get the remote commit before pulling
                    remote_commit = subprocess.run(
                        ["git", "rev-parse", "--short", "origin/HEAD"], 
                        check=True, capture_output=True, text=True
                    ).stdout.strip()
                    
                    # Pull updates
                    subprocess.run(["git", "pull"], check=True, capture_output=True, text=True)
                    new_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
                    
                    if current_commit != new_commit:
                        # Get detailed commit information
                        git_commits = get_git_commit_details(current_commit, new_commit)
                        needs_restart = True
                        git_updated = True
                except Exception as e:
                    print(f"{RED}Warning: Failed to pull git updates: {str(e)}{RESET}")

        # Continue with pip package updates check
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', '--dry-run', '--pre', '-r', 'requirements.txt', '--break-system-packages'],
            capture_output=True,
            text=True
        )

        # Clean up the pip output to remove requirements.txt references
        cleaned_output = re.sub(r'\(from -r requirements\.txt \(line \d+\)\)', '', result.stdout)

        if "Would install" in result.stdout:
            # Parse the pip update output to get package version information
            pip_updates = parse_pip_updates(result.stdout)
            
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
                    print(f"{RED}Warning: Failed to auto-update: {str(e)}{RESET}")

        # Only restart if either git or pip updates were applied
        if needs_restart:
            print("\n")            
            if git_updated:
                print(f"{YELLOW}Git Repository Updates:{RESET}")
                print(f"{BLUE}From commit {current_commit} to {new_commit}{RESET}")
                
                # Display commit messages
                for i, commit in enumerate(git_commits):
                    if i < 5:  # Limit to 5 commits to avoid flooding the console
                        message = commit['message']
                        if len(message) > 50:
                            message = message[:47] + "..."
                        print(f"{BLUE}• {commit['hash']}: {message}{RESET}")
                
                if len(git_commits) > 5:
                    print(f"{BLUE}• ... and {len(git_commits) - 5} more commits{RESET}")
            
            if pip_updated:
                print(f"{YELLOW}Python Package Updates:{RESET}")
                
                # Display package updates
                if pip_updates:
                    for i, update in enumerate(pip_updates):
                        if i < 5:  # Limit to 5 package updates to avoid flooding the console
                            package = update['package']
                            old_version = update['old_version']
                            new_version = update['new_version']
                            print(f"{BLUE}• {package}: {old_version} → {new_version}{RESET}")
                    
                    if len(pip_updates) > 5:
                        print(f"{BLUE}• ... and {len(pip_updates) - 5} more packages{RESET}")
                else:
                    # If pip_updates is empty but pip_updated is True, something went wrong with parsing
                    print(f"{RED}• Failed to parse package details{RESET}")
            
            print(f"{BLUE}The bot will restart to apply these updates{RESET}")
            
            # Import and call restart function
            from scripts.restart import restart_bot
            restart_bot()
    except Exception as e:
        print(f"{RED}Warning: Error checking for updates: {str(e)}{RESET}")

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