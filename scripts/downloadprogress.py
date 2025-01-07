import discord
import time
from datetime import datetime

class DownloadProgress:
    def __init__(self, status_msg, view):
        self.status_msg = status_msg
        self.view = view
        self.last_update = 0
        self.title = ""
        
    def create_progress_bar(self, percentage, width=20):
        filled = int(width * (percentage / 100))
        bar = "█" * filled + "░" * (width - filled)
        return bar
        
    async def progress_hook(self, d):
        if d['status'] == 'downloading':
            current_time = time.time()
            if current_time - self.last_update < 1:
                return
                
            self.last_update = current_time
            
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                speed = d.get('speed', 0)
                if total == 0:
                    return
                percentage = (downloaded / total) * 100
                progress_bar = self.create_progress_bar(percentage)
                speed_mb = speed / 1024 / 1024 if speed else 0  
                status = f"Downloading: {self.title}\n"
                status += f"\n{progress_bar} {percentage:.1f}%\n"
                status += f"Speed: {speed_mb:.1f} MB/s"       
                embed = discord.Embed(
                    title="Downloading",
                    description=status,
                    color=0xf1c40f,
                    timestamp=datetime.now()
                )
                await self.status_msg.edit(embed=embed)               
            except Exception as e:
                print(f"Error updating progress: {str(e)}")