import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.duration import get_audio_duration

def format_duration(duration):
    """Format duration in seconds to mm:ss or hh:mm:ss"""
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.page_size = 10
        self.queue_messages = {}
        self.queue_contexts = {}  # Store original contexts

    def create_queue_buttons(self, current_page, total_pages):
        """Create navigation buttons for queue pagination"""
        view = discord.ui.View()
        
        # Previous page button
        prev_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="⬅️",
            custom_id="prev_page",
            disabled=(current_page == 1)
        )
        
        # Next page button
        next_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="➡️",
            custom_id="next_page",
            disabled=(current_page == total_pages)
        )
        
        async def prev_callback(interaction):
            original_ctx = self.queue_contexts.get(interaction.message.id)
            if original_ctx:
                await self.update_queue_page(interaction, current_page - 1, original_ctx)
            
        async def next_callback(interaction):
            original_ctx = self.queue_contexts.get(interaction.message.id)
            if original_ctx:
                await self.update_queue_page(interaction, current_page + 1, original_ctx)
            
        prev_button.callback = prev_callback
        next_button.callback = next_callback
        
        if total_pages > 1:
            view.add_item(prev_button)
            view.add_item(next_button)
            
        return view

    async def get_queue_embed(self, ctx, page=1):
        """Get the queue embed for a specific page"""
        from bot import music_bot
        
        if not music_bot.current_song and not music_bot.queue and music_bot.download_queue.empty():
            return create_embed("Queue is empty", "Nothing is in the queue", color=0xe74c3c, ctx=ctx), 0

        queue_text = ""
        shown_songs = set()
        total_songs = 0

        if music_bot.current_song:
            queue_text += "**Now playing:**\n"
            loop_cog = self.bot.get_cog('Loop')
            is_looping = loop_cog and music_bot.current_song['url'] in loop_cog.looped_songs
            
            # Get duration for current song
            if not music_bot.current_song.get('is_stream'):
                file_path = music_bot.current_song['file_path']
                duration = music_bot.duration_cache.get(file_path)
                if duration is None:
                    duration = await get_audio_duration(file_path)
                    if duration > 0:
                        music_bot.duration_cache[file_path] = duration
                duration_str = f" `[{format_duration(duration)}]`" if duration > 0 else ""
            else:
                duration_str = " `[LIVE]`"
                
            queue_text += f"[{music_bot.current_song['title']}]({music_bot.current_song['url']}){duration_str}"
            if is_looping:
                queue_text += " - :repeat:"
            queue_text += "\n\n"

        if music_bot.queue:
            loop_cog = self.bot.get_cog('Loop')
            current_song_url = music_bot.current_song['url'] if music_bot.current_song else None
            is_looping = loop_cog and current_song_url in loop_cog.looped_songs
            
            # First check if there are any non-looping songs to show
            has_non_looping_songs = False
            for song in music_bot.queue:
                if not (is_looping and song['url'] == current_song_url):
                    has_non_looping_songs = True
                    break
            
            if has_non_looping_songs:
                queue_text += "**Up Next:**\n"
                position = 1
                start_idx = (page - 1) * self.page_size
                end_idx = start_idx + self.page_size
                
                for song in music_bot.queue:
                    # Skip showing the looped song in queue
                    if is_looping and song['url'] == current_song_url:
                        continue
                        
                    song_title = song['title']
                    if song_title not in shown_songs:
                        total_songs += 1
                        if start_idx <= total_songs - 1 < end_idx:
                            # Get duration for queued song
                            if not song.get('is_stream'):
                                file_path = song['file_path']
                                duration = music_bot.duration_cache.get(file_path)
                                if duration is None:
                                    duration = await get_audio_duration(file_path)
                                    if duration > 0:
                                        music_bot.duration_cache[file_path] = duration
                                duration_str = f" `[{format_duration(duration)}]`" if duration > 0 else ""
                            else:
                                duration_str = " `[LIVE]`"
                                
                            queue_text += f"`{total_songs}.` [{song_title}]({song['url']}){duration_str}\n"
                        shown_songs.add(song_title)
                    
                # Calculate total duration of all songs
                total_duration = 0
                for song in music_bot.queue:
                    if not song.get('is_stream') and not (is_looping and song['url'] == current_song_url):
                        file_path = song['file_path']
                        duration = music_bot.duration_cache.get(file_path)
                        if duration is None:
                            duration = await get_audio_duration(file_path)
                            if duration > 0:
                                music_bot.duration_cache[file_path] = duration
                        total_duration += duration
                
                # Add current song duration if it exists and isn't a stream
                if music_bot.current_song and not music_bot.current_song.get('is_stream'):
                    file_path = music_bot.current_song['file_path']
                    duration = music_bot.duration_cache.get(file_path)
                    if duration is None:
                        duration = await get_audio_duration(file_path)
                        if duration > 0:
                            music_bot.duration_cache[file_path] = duration
                    total_duration += duration
                
                if total_duration > 0:
                    queue_text += f"\nTotal duration: `{format_duration(total_duration)}`"

        if not music_bot.download_queue.empty():
            queue_text += "\n**Downloading:**\n"
            downloading_count = music_bot.download_queue.qsize()
            queue_text += f"{downloading_count} song(s) in download queue\n"

        embed = create_embed(
            f"Queue",
            queue_text if queue_text else "Queue is empty",
            color=0x3498db,
            ctx=ctx
        )
        return embed, total_songs

    async def update_queue_page(self, interaction, new_page, original_ctx):
        """Update the queue message with a new page"""
        embed, total_songs = await self.get_queue_embed(original_ctx, new_page)
        total_pages = (total_songs + self.page_size - 1) // self.page_size
        view = self.create_queue_buttons(new_page, total_pages)
        await interaction.response.edit_message(embed=embed, view=view)

    @commands.command(name='queue', aliases=['playing'])
    @check_dj_role()
    async def queue(self, ctx):
        """Show the current queue"""
        page = 1
        embed, total_songs = await self.get_queue_embed(ctx, page)
        total_pages = (total_songs + self.page_size - 1) // self.page_size
        view = self.create_queue_buttons(page, total_pages)
        
        # Send the initial message with buttons
        message = await ctx.send(embed=embed, view=view)
        self.queue_messages[ctx.channel.id] = message
        self.queue_contexts[message.id] = ctx  # Store the original context

async def setup(bot):
    await bot.add_cog(QueueCog(bot))