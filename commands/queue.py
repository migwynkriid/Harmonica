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

    @commands.command(name='queue', aliases=['playing'])
    @check_dj_role()
    async def queue(self, ctx):
        """Show the current queue"""
        from bot import music_bot
        
        if not music_bot.current_song and not music_bot.queue and music_bot.download_queue.empty():
            await ctx.send(embed=create_embed("Queue is empty", "Nothing is in the queue", color=0xe74c3c, ctx=ctx))
            return

        queue_text = ""
        position = 1

        if music_bot.current_song:
            queue_text += "**Now playing:**\n"
            loop_cog = self.bot.get_cog('Loop')
            is_looping = loop_cog and music_bot.current_song['url'] in loop_cog.looped_songs
            
            # Get duration for current song
            if not music_bot.current_song.get('is_stream'):
                file_path = music_bot.current_song['file_path']
                duration = music_bot.duration_cache.get(file_path)
                if duration is None:
                    duration = get_audio_duration(file_path)
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
                shown_songs = set()  # Track which songs we've already shown
                position = 1
                
                for song in music_bot.queue:
                    # Skip showing the looped song in queue
                    if is_looping and song['url'] == current_song_url:
                        continue
                        
                    song_title = song['title']
                    if song_title not in shown_songs:
                        if position <= 10:  # Only show first 10 songs
                            # Get duration for queued song
                            if not song.get('is_stream'):
                                file_path = song['file_path']
                                duration = music_bot.duration_cache.get(file_path)
                                if duration is None:
                                    duration = get_audio_duration(file_path)
                                    if duration > 0:
                                        music_bot.duration_cache[file_path] = duration
                                duration_str = f" `[{format_duration(duration)}]`" if duration > 0 else ""
                            else:
                                duration_str = " `[LIVE]`"
                                
                            queue_text += f"`{position}.` [{song_title}]({song['url']}){duration_str}\n"
                        shown_songs.add(song_title)
                        position += 1
                
                # If there are more than 10 songs, show the count of remaining songs
                if len(shown_songs) > 10:
                    remaining_songs = len(shown_songs) - 10
                    queue_text += f"\n+`{remaining_songs}` more in queue waiting to play"
                    
                # Calculate total duration of all songs
                total_duration = 0
                for song in music_bot.queue:
                    if not song.get('is_stream') and not (is_looping and song['url'] == current_song_url):
                        file_path = song['file_path']
                        duration = music_bot.duration_cache.get(file_path)
                        if duration is None:
                            duration = get_audio_duration(file_path)
                            if duration > 0:
                                music_bot.duration_cache[file_path] = duration
                        total_duration += duration
                
                # Add current song duration if it exists and isn't a stream
                if music_bot.current_song and not music_bot.current_song.get('is_stream'):
                    file_path = music_bot.current_song['file_path']
                    duration = music_bot.duration_cache.get(file_path)
                    if duration is None:
                        duration = get_audio_duration(file_path)
                        if duration > 0:
                            music_bot.duration_cache[file_path] = duration
                    total_duration += duration
                
                if total_duration > 0:
                    queue_text += f"\nTotal duration: `{format_duration(total_duration)}`\n"

        if not music_bot.download_queue.empty():
            queue_text += "\n**Downloading:**\n"
            downloading_count = music_bot.download_queue.qsize()
            queue_text += f"{downloading_count} song(s) in download queue\n"

        total_songs = (1 if music_bot.current_song else 0) + len(music_bot.queue)
        embed = create_embed(
            f"Queue",
            queue_text if queue_text else "Queue is empty",
            color=0x3498db,
            ctx=ctx
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(QueueCog(bot))