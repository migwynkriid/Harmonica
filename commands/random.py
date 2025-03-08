import discord
import logging
import aiohttp
import random
import yt_dlp
import os
from pathlib import Path
from discord.ext import commands
from scripts.config import YTDL_OPTIONS, BASE_YTDL_OPTIONS
from scripts.messages import create_embed
from scripts.process_queue import process_queue

logger = logging.getLogger(__name__)

class RandomCommand(commands.Cog):
    """
    Command cog for playing random songs.
    
    This cog handles the 'random' command, which plays a song based on a
    randomly selected word fetched from a random word API.
    """
    
    def __init__(self, bot):
        """
        Initialize the RandomCommand cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.random_word_api = "https://random-word-api.herokuapp.com/word"
        self.cookie_file = Path(__file__).parent.parent / 'cookies.txt'  # Path to cookies file

    async def fetch_random_word(self):
        """
        Fetch a random word from the Random Word API.
        
        Returns:
            str: A random word, or None if the API request fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.random_word_api) as response:
                    if response.status == 200:
                        words = await response.json()
                        return words[0] if words else None
                    else:
                        logger.error(f"Failed to fetch random word. Status: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching random word: {str(e)}")
            return None

    async def search_youtube(self, query):
        """
        Search YouTube for videos using yt-dlp.
        
        Args:
            query (str): The search query
            
        Returns:
            dict: Information about the first search result, or None if no results
        """
        try:
            search_opts = {
                **BASE_YTDL_OPTIONS,
                'cookies': str(self.cookie_file) if self.cookie_file.exists() else None,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': 'ytsearch5'  # Limit to 5 results
            }
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                if 'entries' not in info or not info['entries']:
                    return None
                # Return the first valid result
                return info['entries'][0]
        except Exception as e:
            logger.error(f"Error searching YouTube: {str(e)}")
            return None

    @commands.command(name='random')
    async def random_command(self, ctx):
        """
        Play a random song based on a randomly selected word.
        
        This command fetches a random word from an API, searches YouTube
        for music related to that word, and adds the first result to the queue.
        
        Args:
            ctx: The command context
        """
        from bot import MusicBot
        music_bot = MusicBot.get_instance(str(ctx.guild.id))
        
        try:
            # Check if user is in a voice channel
            if not ctx.author.voice:
                embed = create_embed("Error", "You must be in a voice channel to use this command!", discord.Color.red(), ctx=ctx)
                await ctx.send(embed=embed)
                return

            # Connect to voice channel if needed
            if not ctx.guild.voice_client:
                try:
                    await ctx.author.voice.channel.connect()
                except discord.ClientException as e:
                    if "already connected" in str(e):
                        # If already connected but in a different state, clean up and reconnect
                        if music_bot.voice_client:
                            await music_bot.voice_client.disconnect()
                        music_bot.voice_client = None
                        await ctx.author.voice.channel.connect()
                    else:
                        raise e
            elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
                await ctx.guild.voice_client.move_to(ctx.author.voice.channel)

            music_bot.voice_client = ctx.guild.voice_client
            
            # Show single status message
            status_msg = await ctx.send(embed=create_embed("Feeling lucky?", "Searching for something ✨", discord.Color.blue(), ctx=ctx))
            
            # Fetch random word
            word = await self.fetch_random_word()
            
            if not word:
                await status_msg.edit(embed=create_embed("Error", "Failed to fetch a random word. Please try again.", discord.Color.red(), ctx=ctx))
                await status_msg.delete(delay=5)  # Delete after 5 seconds
                return

            # Search using the word
            search_query = f"{word} music"
            result = await self.search_youtube(search_query)
            if not result:
                await status_msg.edit(embed=create_embed("Error", f"No results found for '{search_query}'. Trying another word...", discord.Color.orange(), ctx=ctx))
                await status_msg.delete(delay=5)  # Delete after 5 seconds
                return
            
            # Download the song using the URL
            download_result = await music_bot.download_song(result['url'], status_msg=status_msg, ctx=ctx, skip_url_check=True)
            if not download_result:
                await status_msg.delete(delay=5)  # Delete after 5 seconds
                return

            # Add to queue
            async with music_bot.queue_lock:
                music_bot.queue.append({
                    'title': download_result['title'],
                    'url': download_result['url'],
                    'file_path': download_result['file_path'],
                    'thumbnail': download_result.get('thumbnail'),
                    'ctx': ctx,
                    'is_stream': download_result.get('is_stream', False),
                    'is_from_playlist': False,
                    'requester': ctx.author
                })

                # Check if we should start playing
                should_play = not music_bot.is_playing and not music_bot.waiting_for_song
                if music_bot.voice_client:
                    should_play = should_play and not music_bot.voice_client.is_playing()
                else:
                    should_play = True

            # Start playing if needed
            if should_play:
                await status_msg.delete()  # Delete the "Feeling lucky?" message
                await process_queue(music_bot, ctx)
            else:
                queue_pos = len(music_bot.queue)
                # Check if current song is looped
                loop_cog = self.bot.get_cog('Loop')
                description = f"[🎵 {download_result['title']}]({download_result['url']})"
                
                # Only show position if current song is not looping
                if music_bot.current_song:
                    current_song_url = music_bot.current_song['url']
                    is_current_looping = loop_cog and current_song_url in loop_cog.looped_songs
                    if not is_current_looping:
                        description += f"\nPosition in queue: {queue_pos}"
                    
                queue_embed = create_embed(
                    "Added to Queue",
                    description,
                    color=0x3498db,
                    thumbnail_url=download_result.get('thumbnail'),
                    ctx=ctx
                )
                await status_msg.delete()  # Delete the "Feeling lucky?" message
                queue_msg = await ctx.send(embed=queue_embed)
                music_bot.queued_messages[download_result['url']] = queue_msg

        except Exception as e:
            logger.error(f"Error in random command: {str(e)}")
            if 'status_msg' in locals():
                await status_msg.delete()  # Delete the "Feeling lucky?" message
            embed = create_embed("Error", f"An error occurred: {str(e)}", discord.Color.red(), ctx=ctx)
            error_msg = await ctx.send(embed=embed)
            await error_msg.delete(delay=5)  # Delete error message after 5 seconds

async def setup(bot):
    """
    Setup function to add the RandomCommand cog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(RandomCommand(bot))