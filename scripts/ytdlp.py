import os
import sys
import urllib.request
import platform

def get_ytdlp_path():
    local_path = os.path.join(os.getcwd(), 'yt-dlp')
    if os.path.exists(local_path):
        return local_path
    return 'yt-dlp'

async def ytdlp_version(ctx):
        """Check the version of the locally installed yt-dlp"""
        try:
            ytdlp_path = get_ytdlp_path()
            if not ytdlp_path:
                await ctx.send(embed=self.create_embed("Error", "yt-dlp executable not found", color=0xe74c3c))
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
                embed = self.create_embed("yt-dlp Version", f"yt-dlp: {version}", color=0x3498db)
                embed.add_field(name="Version Code", value="22", inline=False)
                await ctx.send(embed=embed)
            else:
                error = stderr.decode().strip()
                await ctx.send(embed=self.create_embed("Error", f"Failed to get yt-dlp version: {error}", color=0xe74c3c))
        except Exception as e:
            await ctx.send(embed=self.create_embed("Error", f"Error checking yt-dlp version: {str(e)}", color=0xe74c3c))