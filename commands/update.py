from discord.ext import commands
import os
import sys
import subprocess
from scripts.messages import create_embed
from scripts.constants import EMBED_COLOR_ERROR, EMBED_COLOR_SUCCESS
from scripts.config import load_config

# Get Git repository URL from config (allows users with forks to set their own)
config = load_config()
GIT_REPO_URL = config.get('GITHUB_REPO')


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
    try:
        # Send initial status message
        status_msg = await ctx.send(embed=create_embed("Updating bot...", "Installing required packages...", color=EMBED_COLOR_SUCCESS, ctx=ctx))
        
        # Get current commit hash and count before update
        try:
            current_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
            current_count = subprocess.run(["git", "rev-list", "--count", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError:
            current_commit = "unknown"
            current_count = "?"
        
        # Git pull from repository to update code
        try:
            subprocess.run(["git", "pull", GIT_REPO_URL], check=True, capture_output=True, text=True)
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
        
        embed = create_embed("Update Complete!", description, color=EMBED_COLOR_SUCCESS, ctx=ctx)
        await status_msg.edit(embed=embed)
    except Exception as e:
        await ctx.send(embed=create_embed("Error", f"Error during update: {str(e)}", color=EMBED_COLOR_ERROR, ctx=ctx))