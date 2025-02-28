import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.duration import get_audio_duration

def format_duration(duration):
    """
    Format duration in seconds to mm:ss or hh:mm:ss format.
    
    Args:
        duration (float): Duration in seconds
        
    Returns:
        str: Formatted duration string in mm:ss or hh:mm:ss format
    """
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

class QueueCog(commands.Cog):
    """
    Command cog for displaying and managing the music queue.
    
    This cog handles the 'queue' command, which displays the current song,
    upcoming songs, and songs being downloaded. It supports pagination for
    large queues.
    """
    
    def __init__(self, bot):
        """
        Initialize the QueueCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self._last_member = None
        self.page_size = 10  # Number of songs to display per page
        self.queue_messages = {}  # Store queue messages by channel ID
        self.queue_contexts = {}  # Store original contexts by message ID

    def create_queue_buttons(self, current_page, total_pages):
        """
        Create navigation buttons for queue pagination.
        
        Creates a Discord UI View with previous and next page buttons
        for navigating through the queue pages.
        
        Args:
            current_page (int): The current page number
            total_pages (int): The total number of pages
            
        Returns:
            discord.ui.View: View containing the navigation buttons
        """
        view = discord.ui.View()
        
        # Previous page button
        prev_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="⬅️",
            custom_id="prev_page",
            disabled=(current_page == 1)  # Disable if on first page
        )
        
        # Next page button
        next_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="➡️",
            custom_id="next_page",
            disabled=(current_page == total_pages)  # Disable if on last page
        )
        
        async def prev_callback(interaction):
            """Callback for the previous page button"""
            original_ctx = self.queue_contexts.get(interaction.message.id)
            if original_ctx:
                await self.update_queue_page(interaction, current_page - 1, original_ctx)
            
        async def next_callback(interaction):
            """Callback for the next page button"""
            original_ctx = self.queue_contexts.get(interaction.message.id)
            if original_ctx:
                await self.update_queue_page(interaction, current_page + 1, original_ctx)
            
        prev_button.callback = prev_callback
        next_button.callback = next_callback
        
        # Only add buttons if there are multiple pages
        if total_pages > 1:
            view.add_item(prev_button)
            view.add_item(next_button)
            
        return view

    async def get_queue_embed(self, ctx, page=1):
        """
        Get the queue embed for a specific page.
        
        Creates an embed displaying the current song, upcoming songs,
        and songs being downloaded. Supports pagination for large queues.
        
        Args:
            ctx: The command context
            page (int): The page number to display
            
        Returns:
            tuple: (discord.Embed, int) - The queue embed and total number of songs
        """
        from bot import MusicBot
        
        # Get server-specific music bot instance
        server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
        
        # Return empty queue message if nothing is playing or queued
        if not server_music_bot.current_song and not server_music_bot.queue and server_music_bot.download_queue.empty():
            return create_embed("Queue is empty", "Nothing is in the queue", color=0xe74c3c, ctx=ctx), 0

        queue_text = ""
        shown_songs = set()  # Track shown songs to avoid duplicates
        total_songs = 0

        # Display current song if there is one
        if server_music_bot.current_song:
            queue_text += "**Now playing:**\n"
            loop_cog = self.bot.get_cog('Loop')
            is_looping = loop_cog and server_music_bot.current_song['url'] in loop_cog.looped_songs
            
            # Get duration for current song
            if not server_music_bot.current_song.get('is_stream'):
                file_path = server_music_bot.current_song['file_path']
                duration = server_music_bot.duration_cache.get(file_path)
                if duration is None:
                    # Calculate duration if not cached
                    duration = await get_audio_duration(file_path)
                    if duration > 0:
                        server_music_bot.duration_cache[file_path] = duration
                duration_str = f" `[{format_duration(duration)}]`" if duration > 0 else ""
            else:
                duration_str = " `[LIVE]`"  # Live streams don't have duration
                
            # Format the current song with title, URL, and duration
            queue_text += f"[{server_music_bot.current_song['title']}]({server_music_bot.current_song['url']}){duration_str}"
            if is_looping:
                queue_text += " - :repeat:"  # Add repeat icon if song is looping
            queue_text += "\n\n"

        # Display upcoming songs if there are any
        if server_music_bot.queue:
            loop_cog = self.bot.get_cog('Loop')
            current_song_url = server_music_bot.current_song['url'] if server_music_bot.current_song else None
            is_looping = loop_cog and current_song_url in loop_cog.looped_songs
            
            # First check if there are any non-looping songs to show
            has_non_looping_songs = False
            for song in server_music_bot.queue:
                if not (is_looping and song['url'] == current_song_url):
                    has_non_looping_songs = True
                    break
            
            if has_non_looping_songs:
                queue_text += "**Up Next:**\n"
                position = 1
                start_idx = (page - 1) * self.page_size  # Calculate pagination indices
                end_idx = start_idx + self.page_size
                
                for song in server_music_bot.queue:
                    # Skip showing the looped song in queue (it will play next anyway)
                    if is_looping and song['url'] == current_song_url:
                        continue
                        
                    song_title = song['title']
                    if song_title not in shown_songs:  # Avoid showing duplicate songs
                        total_songs += 1
                        if start_idx <= total_songs - 1 < end_idx:  # Only show songs for current page
                            # Get duration for queued song
                            if not song.get('is_stream'):
                                file_path = song['file_path']
                                duration = server_music_bot.duration_cache.get(file_path)
                                if duration is None:
                                    duration = await get_audio_duration(file_path)
                                    if duration > 0:
                                        server_music_bot.duration_cache[file_path] = duration
                                duration_str = f" `[{format_duration(duration)}]`" if duration > 0 else ""
                            else:
                                duration_str = " `[LIVE]`"
                                
                            # Format each queued song with position, title, URL, and duration
                            queue_text += f"`{total_songs}.` [{song_title}]({song['url']}){duration_str}\n"
                        shown_songs.add(song_title)  # Mark song as shown
                    
        # Display downloading songs if there are any
        if not server_music_bot.download_queue.empty():
            queue_text += "\n**Downloading:**\n"
            downloading_count = server_music_bot.download_queue.qsize()
            queue_text += f"{downloading_count} song(s) in download queue\n"

        # Create the final embed
        embed = create_embed(
            f"Queue",
            queue_text if queue_text else "Queue is empty",
            color=0x3498db,
            ctx=ctx
        )
        return embed, total_songs

    async def update_queue_page(self, interaction, new_page, original_ctx):
        """
        Update the queue message with a new page.
        
        This method is called when a user clicks on a pagination button.
        It updates the queue message with the content of the new page.
        
        Args:
            interaction: The button interaction
            new_page (int): The new page number to display
            original_ctx: The original command context
        """
        embed, total_songs = await self.get_queue_embed(original_ctx, new_page)
        total_pages = (total_songs + self.page_size - 1) // self.page_size
        view = self.create_queue_buttons(new_page, total_pages)
        await interaction.response.edit_message(embed=embed, view=view)

    @commands.command(name='queue', aliases=['playing'])
    @check_dj_role()
    async def queue(self, ctx):
        """
        Show the current queue.
        
        Displays the current song, upcoming songs, and songs being downloaded.
        Supports pagination for large queues with interactive buttons.
        
        Args:
            ctx: The command context
        """
        page = 1  # Start with the first page
        embed, total_songs = await self.get_queue_embed(ctx, page)
        total_pages = (total_songs + self.page_size - 1) // self.page_size
        view = self.create_queue_buttons(page, total_pages)
        
        # Send the initial message with buttons
        message = await ctx.send(embed=embed, view=view)
        self.queue_messages[ctx.channel.id] = message
        self.queue_contexts[message.id] = ctx  # Store the original context for button callbacks

async def setup(bot):
    """
    Setup function to add the QueueCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(QueueCog(bot))