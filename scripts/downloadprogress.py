import discord
import time
import concurrent.futures
from datetime import datetime
from scripts.format_size import format_size
from scripts.config import load_config
import asyncio

config_vars = load_config()
SHOW_PROGRESS_BAR = config_vars.get('MESSAGES', {}).get('SHOW_PROGRESS_BAR', True)

class DownloadProgress:
    """
    Handles the display and updating of download progress in Discord messages.
    
    This class creates and updates embeds with download progress information,
    including progress bars, file sizes, and video information.
    """
    
    def __init__(self, status_msg, view):
        """
        Initialize the download progress tracker.
        
        Args:
            status_msg: The Discord message object to update with progress
            view: The Discord UI view associated with the message
        """
        self.status_msg = status_msg
        self.view = view
        self.last_update = 0
        self.title = ""
        self.ctx = None  # Store ctx for footer info
        self.download_complete = False  # Track if download is complete
        
    def create_progress_bar(self, percentage, width=20):
        """
        Create a text-based progress bar.
        
        Args:
            percentage: The percentage of completion (0-100)
            width: The width of the progress bar in characters
            
        Returns:
            str: A text-based progress bar using block characters
        """
        filled = int(width * (percentage / 100))
        bar = "▓" * filled + "░" * (width - filled)
        return bar
        
    def progress_hook(self, d):
        """
        Hook function called by yt-dlp during the download process.
        
        This method is called repeatedly during a download to update
        the progress display. It creates an embed with download information
        and updates the status message.
        
        Args:
            d: Dictionary containing download information from yt-dlp
        """
        if d['status'] == 'downloading':
            current_time = time.time()
            if current_time - self.last_update < 2:
                return
                
            self.last_update = current_time
            
            try:
                if d['status'] == 'finished':
                    self.download_complete = True
                    return
                    
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
                status = f"[{video_title}]({video_url})\n"
                
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
                
                # Use asyncio.create_task to run the message edit in the background
                if self.status_msg:
                    try:
                        # First try to get the event loop from the running context
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        # If that fails, get a new event loop
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    if loop.is_running():
                        # Use run_coroutine_threadsafe without timeout to avoid the error
                        future = asyncio.run_coroutine_threadsafe(
                            self.status_msg.edit(embed=embed, view=self.view),
                            loop
                        )
                        # Optionally wait for the result but don't use timeout
                        try:
                            future.result(0.5)  # Wait for a short time but don't block indefinitely
                        except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                            pass  # Ignore timeout, the update will happen asynchronously
                    else:
                        # If loop is not running, create a new task
                        loop.run_until_complete(self.status_msg.edit(embed=embed, view=self.view))
            except Exception as e:
                print(f"Error updating progress: {str(e)}")