import discord
import time
from datetime import datetime
from scripts.format_size import format_size
from scripts.config import load_config

config_vars = load_config()
SHOW_PROGRESS_BAR = config_vars.get('MESSAGES', {}).get('SHOW_PROGRESS_BAR', True)

class DownloadProgress:
    def __init__(self, status_msg, view):
        self.status_msg = status_msg
        self.view = view
        self.last_update = 0
        self.title = ""
        self.ctx = None  # Store ctx for footer info
        
    def create_progress_bar(self, percentage, width=20):
        filled = int(width * (percentage / 100))
        bar = "▓" * filled + "░" * (width - filled)
        return bar
        
    async def progress_hook(self, d):
        if d['status'] == 'downloading':
            current_time = time.time()
            if current_time - self.last_update < 2:
                return
                
            self.last_update = current_time
            
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                if total == 0:
                    return
                percentage = (downloaded / total) * 100
                downloaded_size = format_size(downloaded)
                total_size = format_size(total)
                info = d.get('info_dict', {})
                video_title = info.get('title', self.title)
                video_url = info.get('webpage_url', '')
                status = f"Downloading: [{video_title}]({video_url})\n"
                
                if SHOW_PROGRESS_BAR:
                    progress_bar = self.create_progress_bar(percentage)
                    status += f"{progress_bar}\n\n"
                
                status += f"Size: {downloaded_size} / {total_size}"
                embed = discord.Embed(
                    title="Downloading",
                    description=status,
                    color=0x3498db,
                    timestamp=datetime.now()
                )
                # Add thumbnail if available
                thumbnail_url = info.get('thumbnail')
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)
                if self.ctx and hasattr(self.ctx, 'author') and self.ctx.author:
                    embed.set_footer(
                        text=f"Requested by {self.ctx.author.display_name}",
                        icon_url=self.ctx.author.display_avatar.url
                    )
                await self.status_msg.edit(embed=embed)               
            except Exception as e:
                print(f"Error updating progress: {str(e)}")