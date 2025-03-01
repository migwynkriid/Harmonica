import discord
import time
import concurrent.futures
from datetime import datetime
from scripts.format_size import format_size
from scripts.config import load_config
import asyncio
import functools

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
        self.message_queue = asyncio.Queue()
        self.update_task = None
        
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
    
    def start_updater(self, loop=None):
        """
        Start the message updater task.
        
        Args:
            loop: The event loop to use for the task
        """
        if self.update_task is None or self.update_task.done():
            if loop is None:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            
            self.update_task = loop.create_task(self._message_updater())
    
    async def _message_updater(self):
        """
        Background task that processes message updates from the queue.
        """
        try:
            while True:
                try:
                    # Get the next message update from the queue with a timeout
                    # This allows the task to be cancelled properly
                    try:
                        embed = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # Check if we should exit
                        if self.download_complete and self.message_queue.empty():
                            break
                        continue
                    
                    # Update the message
                    if self.status_msg:
                        try:
                            await self.status_msg.edit(embed=embed, view=self.view)
                        except Exception as e:
                            print(f"Error updating message: {str(e)}")
                    
                    # Mark the task as done
                    self.message_queue.task_done()
                    
                    # Small delay to prevent rate limiting
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    # Handle task cancellation
                    break
                except Exception as e:
                    print(f"Error in message updater: {str(e)}")
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Handle task cancellation
            pass
    
    async def cleanup(self):
        """
        Clean up resources and cancel the update task.
        
        This method should be called when the download is complete
        or when the bot is shutting down.
        """
        self.download_complete = True
        
        # Wait for the queue to be empty
        if not self.message_queue.empty():
            try:
                await asyncio.wait_for(self.message_queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
        
        # Cancel the update task if it's running
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
            try:
                await asyncio.wait_for(self.update_task, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        self.update_task = None
    
    def progress_hook(self, d):
        """
        Hook function called by yt-dlp during the download process.
        
        This method is called repeatedly during a download to update
        the progress display. It creates an embed with download information
        and adds it to the update queue.
        
        Args:
            d: Dictionary containing download information from yt-dlp
        """
        if d['status'] == 'downloading':
            # Throttle updates to avoid too many message edits
            current_time = time.time()
            if current_time - self.last_update < 2:
                return
                
            self.last_update = current_time
            
            try:
                # Check if download is finished
                if d.get('status') == 'finished':
                    self.download_complete = True
                    return
                
                # Extract download information
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                if total == 0:
                    return
                    
                # Calculate progress percentage and format sizes
                percentage = (downloaded / total) * 100
                downloaded_size = format_size(downloaded)
                total_size = format_size(total)
                
                # Get video information
                info = d.get('info_dict', {})
                video_title = info.get('title', self.title)
                video_url = info.get('webpage_url', '')
                
                # Create status message with progress information
                status = f"[{video_title}]({video_url})\n"
                
                if SHOW_PROGRESS_BAR:
                    progress_bar = self.create_progress_bar(percentage)
                    status += f"{progress_bar}\n\n"
                
                status += f"Size: {downloaded_size} / {total_size}"
                
                # Create embed with download information
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
                
                # Add footer with requester information
                if self.ctx and hasattr(self.ctx, 'author') and self.ctx.author:
                    embed.set_footer(
                        text=f"Requested by {self.ctx.author.display_name}",
                        icon_url=self.ctx.author.display_avatar.url
                    )
                
                # Add the embed to the update queue
                if self.status_msg:
                    # Start the updater task if it's not running
                    try:
                        loop = None
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            try:
                                loop = asyncio.get_event_loop()
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                        
                        # Start the message updater if it's not already running
                        self.start_updater(loop)
                        
                        # Add the embed to the queue
                        if not self.message_queue.full():
                            # Use put_nowait to avoid blocking
                            self.message_queue.put_nowait(embed)
                    except Exception as e:
                        print(f"Error queueing message update: {str(e)}")
            except Exception as e:
                print(f"Error in progress hook: {str(e)}")