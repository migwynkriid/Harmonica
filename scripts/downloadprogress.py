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
        self.server_id = None  # Store server ID for multi-server support
        self.message_queues = {}  # Dict to store per-server message queues
        self.update_tasks = {}  # Dict to store per-server update tasks
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
        Start the message updater task for the current server.
        
        Args:
            loop: The event loop to use for the task
        """
        # Try to get server ID from status_msg
        if not self.server_id and self.status_msg and hasattr(self.status_msg, 'guild') and self.status_msg.guild:
            self.server_id = str(self.status_msg.guild.id)
        
        # Try to get server ID from ctx
        if not self.server_id and self.ctx and hasattr(self.ctx, 'guild') and self.ctx.guild:
            self.server_id = str(self.ctx.guild.id)

        # If still no server ID, use a default one
        if not self.server_id:
            self.server_id = "default"  # Use a default server ID instead of showing a warning

        # Initialize queue for this server if not exists
        if self.server_id not in self.message_queues:
            self.message_queues[self.server_id] = asyncio.Queue()

        # Only start a new task if none exists for this server or if it's done
        if self.server_id not in self.update_tasks or self.update_tasks[self.server_id].done():
            if loop is None:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            
            self.update_tasks[self.server_id] = loop.create_task(self._message_updater(self.server_id))

    async def _message_updater(self, server_id):
        """
        Background task that processes message updates from the server's queue.
        
        Args:
            server_id: The ID of the server whose queue to process
        """
        try:
            while True:
                try:
                    # Get the next message update from the queue with a timeout
                    try:
                        embed = await asyncio.wait_for(self.message_queues[server_id].get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # Check if we should exit
                        if self.download_complete and self.message_queues[server_id].empty():
                            break
                        continue
                    
                    # Update the message
                    if self.status_msg:
                        try:
                            await self.status_msg.edit(embed=embed, view=self.view)
                        except Exception as e:
                            print(f"Error updating message for server {server_id}: {str(e)}")
                    
                    # Mark the task as done
                    self.message_queues[server_id].task_done()
                    
                    # Small delay to prevent rate limiting
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error in message updater for server {server_id}: {str(e)}")
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            # Clean up server-specific resources when the task ends
            if server_id in self.update_tasks:
                del self.update_tasks[server_id]
            if server_id in self.message_queues:
                del self.message_queues[server_id]

    async def cleanup(self):
        """
        Clean up resources and cancel update tasks for all servers.
        """
        self.download_complete = True
        
        # Wait for all queues to be empty - use a copy of the keys to avoid modification during iteration
        server_ids = list(self.message_queues.keys())
        for server_id in server_ids:
            if server_id in self.message_queues and not self.message_queues[server_id].empty():
                try:
                    await asyncio.wait_for(self.message_queues[server_id].join(), timeout=5.0)
                except asyncio.TimeoutError:
                    pass
        
        # Cancel all update tasks - use a copy of the keys to avoid modification during iteration
        server_ids = list(self.update_tasks.keys())
        for server_id in server_ids:
            if server_id in self.update_tasks and not self.update_tasks[server_id].done():
                task = self.update_tasks[server_id]
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
        
        # Clear the dictionaries
        self.update_tasks.clear()
        self.message_queues.clear()

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
            current_time = time.time()
            if current_time - self.last_update < 2:
                return
                
            self.last_update = current_time
            
            try:
                if d.get('status') == 'finished':
                    self.download_complete = True
                    return
                
                # Get server ID if not already set
                if not self.server_id and self.status_msg and hasattr(self.status_msg, 'guild') and self.status_msg.guild:
                    self.server_id = str(self.status_msg.guild.id)
                
                # Try to get server ID from ctx
                if not self.server_id and self.ctx and hasattr(self.ctx, 'guild') and self.ctx.guild:
                    self.server_id = str(self.ctx.guild.id)

                # If still no server ID, use a default one
                if not self.server_id:
                    self.server_id = "default"  # Use a default server ID instead of showing a warning

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
                        
                        # Add the embed to the server's queue
                        if not self.message_queues[self.server_id].full():
                            self.message_queues[self.server_id].put_nowait(embed)
                    except Exception as e:
                        print(f"Error queueing message update for server {self.server_id}: {str(e)}")
            except Exception as e:
                print(f"Error in progress hook: {str(e)}")