import os
import sys
import urllib.request
import platform
from scripts.messages import update_or_send_message, create_embed

def get_ytdlp_path():
    """
    Get the path to the yt-dlp executable.
    
    This function checks if yt-dlp exists in the current working directory
    and returns its path if found. Otherwise, it returns just the executable
    name, which will use the system PATH to locate it.
    
    Returns:
        str: Path to the yt-dlp executable
    """
    local_path = os.path.join(os.getcwd(), 'yt-dlp')
    if os.path.exists(local_path):
        return local_path
    return 'yt-dlp'

async def ytdlp_version(ctx):
    """
    Check the version of the locally installed yt-dlp.
    
    This function executes the yt-dlp executable with the --version flag
    to determine the installed version. It creates and sends an embed
    message with the version information or an error message if the
    version check fails.
    
    Args:
        ctx: The command context for sending the response
        
    Returns:
        None: The function sends a message with the version information
    """
    try:
        ytdlp_path = get_ytdlp_path()
        if not ytdlp_path:
            await ctx.send(embed=create_embed("Error", "yt-dlp executable not found", color=0xe74c3c))
            return

        process = await asyncio.create_subprocess_exec(
            ytdlp_path,
            '--version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            version = stdout.decode().strip()
            embed = create_embed("yt-dlp Version", f"yt-dlp: {version}", color=0x3498db)
            embed.add_field(name="Version Code", value="22", inline=False)
            await ctx.send(embed=embed)
        else:
            error = stderr.decode().strip()
            await ctx.send(embed=create_embed("Error", f"Failed to get yt-dlp version: {error}", color=0xe74c3c))
    except Exception as e:
        await ctx.send(embed=create_embed("Error", f"Error checking yt-dlp version: {str(e)}", color=0xe74c3c))