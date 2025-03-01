from discord.ext import commands
import discord
import yt_dlp
import asyncio
import os

async def setup(bot):
    """
    Setup function to add the version command to the bot.
    
    Args:
        bot: The bot instance
    """
    bot.add_command(ytdlp)
    return None

@commands.command(name='version')
async def ytdlp(ctx):
    """
    Check the version of the locally installed yt-dlp and git commit information.
    
    This command displays the version of yt-dlp being used by the bot,
    as well as the current git commit hash and commit count to help
    track which version of the bot is running.
    
    Args:
        ctx: The command context
    """
    try:
        # Send initial status message
        status_msg = await ctx.send(embed=discord.Embed(title="Bot Version", description="Checking versions...", color=0x3498db))
        
        # Get yt-dlp version
        try:
            version = yt_dlp.version.__version__
        except Exception:
            version = "Unknown"

        # Create embed with yt-dlp version
        embed = discord.Embed(title="Bot Version", description=f"yt-dlp: `{version}`", color=0x3498db)
        await status_msg.edit(embed=embed)
            
        # Get git commit hash
        git_hash_process = await asyncio.create_subprocess_exec(
            'git',
            'rev-parse',
            '--short',
            'HEAD',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        hash_stdout, _ = await git_hash_process.communicate()
        
        # Get git commit count
        git_count_process = await asyncio.create_subprocess_exec(
            'git',
            'rev-list',
            '--count',
            'HEAD',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        count_stdout, _ = await git_count_process.communicate()
        
        # Format commit information
        commit_info = "Unknown"
        if git_hash_process.returncode == 0 and git_count_process.returncode == 0:
            commit_hash = hash_stdout.decode().strip()
            commit_count = count_stdout.decode().strip()
            commit_info = f"#{commit_count} (`{commit_hash}`)"
        
        # Add commit info to embed and update message
        embed.add_field(name="Current commit", value=commit_info, inline=False)
        await status_msg.edit(embed=embed)
            
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"An error occurred: {str(e)}", color=0xe74c3c))