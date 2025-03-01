from discord.ext import commands
import discord
import os
import sys
import subprocess
import json
import sys

# Add scripts directory to path for importing ytdlp
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)
OWNER_ID = int(config['OWNER_ID'])

async def setup(bot):
    """
    Setup function to add the update command to the bot.
    
    Args:
        bot: The bot instance
    """
    bot.add_command(updateytdlp)
    return None

@commands.command(name='update')
@commands.is_owner()
async def updateytdlp(ctx):
    """
    Update the bot by pulling from git and installing required packages.
    
    This command performs two main tasks:
    1. Pulls the latest code from the git repository
    2. Updates all packages listed in requirements.txt
    
    This command is restricted to the bot owner only.
    
    Args:
        ctx: The command context
    """
    if ctx.author.id != OWNER_ID:
        await ctx.send(embed=discord.Embed(title="Error", description="This command is only available to the bot owner.", color=0xe74c3c))
        return
    
    try:
        # Send initial status message
        status_msg = await ctx.send(embed=discord.Embed(title="Updating bot...", description="Installing required packages...", color=0x2ecc71))
        
        # Get current commit hash and count before update
        try:
            current_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
            current_count = subprocess.run(["git", "rev-list", "--count", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError:
            current_commit = "unknown"
            current_count = "?"
        
        # Git pull from repository to update code
        try:
            subprocess.run(["git", "pull", "https://github.com/migwynkriid/Harmonica"], check=True, capture_output=True, text=True)
            # Get new commit hash and count after pull
            new_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
            new_count = subprocess.run(["git", "rev-list", "--count", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
            git_updated = True
        except subprocess.CalledProcessError as e:
            git_updated = False
            git_error = e.stderr
        
        # Install packages from requirements.txt
        requirements_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'requirements.txt')
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "--pre", "-r", requirements_path, "--break-system-packages"], check=True, capture_output=True, text=True)
            packages_updated = True
        except subprocess.CalledProcessError as e:
            packages_updated = False
            error_msg = e.stderr
        
        # Create final status message with update results
        description = ""
        if git_updated:
            if current_commit != new_commit:
                description += f"✅ Git repository updated successfully from\n#{current_count} (`{current_commit}`) to #{new_count} (`{new_commit}`)\n"
            else:
                description += "✅ Git repository is already up to date (no new commits)\n"
        else:
            description += f"❌ Failed to update git repository: {git_error}\n"
        if packages_updated:
            description += "✅ Required packages installed successfully\n"
        else:
            description += f"❌ Failed to install packages: {error_msg}\n"
        description += f"\nPlease restart the bot using `{ctx.prefix}restart`"
        
        embed = discord.Embed(title="Update Complete!", description=description, color=0x2ecc71)
        await status_msg.edit(embed=embed)
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"Error during update: {str(e)}", color=0xe74c3c))