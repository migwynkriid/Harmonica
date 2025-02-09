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
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(pytz.utc)
    )
    return embed

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def check_git_updates():
    try:
        # Get current commit hash
        current_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        
        # Fetch latest changes
        subprocess.run(["git", "fetch", "https://github.com/migwynkriid/Harmonica"], check=True, capture_output=True, text=True)
        
        # Get the commit hash of origin/main
        remote_commit = subprocess.run(["git", "rev-parse", "--short", "origin/main"], check=True, capture_output=True, text=True).stdout.strip()
        
        return current_commit != remote_commit
    except subprocess.CalledProcessError:
        return False

async def check_updates(bot):
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
        # Check for pip updates
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', '--dry-run', '--pre', '-r', 'requirements.txt', '--break-system-packages'],
            capture_output=True,
            text=True
        )
        
        has_pip_updates = "Would install" in result.stdout
        has_git_updates = check_git_updates()
        
        if has_pip_updates or has_git_updates:
            # Check if bot is in voice chat
            from bot import music_bot
            is_in_voice = music_bot and music_bot.voice_client and music_bot.voice_client.is_connected()
            
            if not is_in_voice:
                try:
                    if has_pip_updates:
                        # Run actual update command
                        subprocess.run(
                            [sys.executable, '-m', 'pip', 'install', '--upgrade', '--pre', '-r', 'requirements.txt', '--break-system-packages'],
                            check=True,
                            capture_output=True,
                            text=True
                        )
                    
                    if has_git_updates:
                        # Pull latest changes
                        subprocess.run(["git", "pull", "https://github.com/migwynkriid/Harmonica"], check=True, capture_output=True, text=True)
                    
                    # Import and call restart function
                    from scripts.restart import restart_bot
                    restart_bot()
                except Exception as e:
                    print(f"\033[91mWarning: Failed to auto-update: {str(e)}\033[0m")
            # If in voice chat, do nothing and let the hourly check try again
    except Exception as e:
        print(f"\033[91mWarning: Error checking for updates: {str(e)}\033[0m")

@tasks.loop(hours=1)
async def update_checker(bot):
    await check_updates(bot)

async def startup_check(bot):
    await check_updates(bot)

def setup(bot):
    update_checker.start(bot)
    bot.loop.create_task(startup_check(bot))
    bot.add_cog(UpdateScheduler(bot))
