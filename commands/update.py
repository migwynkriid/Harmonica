from discord.ext import commands
import discord
import os
import sys
import subprocess
import json
import sys

# Add scripts directory to path for importing ytdlp
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
from ytdlp import ensure_ytdlp

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)
OWNER_ID = config['OWNER_ID']

async def setup(bot):
    bot.add_command(updateytdlp)
    return None

@commands.command(name='update')
@commands.is_owner()
async def updateytdlp(ctx):
    if ctx.author.id != OWNER_ID:
        await ctx.send(embed=discord.Embed(title="Error", description="This command is only available to the bot owner.", color=0xe74c3c))
        return
    """Update the yt-dlp executable"""
    try:
        status_msg = await ctx.send(embed=discord.Embed(title="Updating yt-dlp...", color=0x2ecc71))
        
        ytdlp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'yt-dlp.exe' if sys.platform.startswith('win') else 'yt-dlp')
        if os.path.exists(ytdlp_path):
            os.remove(ytdlp_path)

        new_path = ensure_ytdlp()
        if not new_path:
            raise Exception("Failed to download yt-dlp")

        try:
            result = subprocess.run([new_path, '--version'], capture_output=True, text=True)
            version = result.stdout.strip()
        except Exception:
            version = "Unknown"
        
        embed = discord.Embed(title="Finished updating!", description=f"Yt-dlp is updated to version `{version}`\nPlease restart the bot using `{ctx.prefix}restart`", color=0x2ecc71)
        await status_msg.edit(embed=embed)
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"Error updating yt-dlp: {str(e)}", color=0xe74c3c))