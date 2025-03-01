import discord
import asyncio
import logging
import yt_dlp
from discord.ext import commands
from scripts.messages import create_embed, update_or_send_message
from scripts.config import BASE_YTDL_OPTIONS, load_config
from scripts.voice import join_voice_channel
from scripts.process_queue import process_queue

class SearchCog(commands.Cog):
    """
    Command cog for searching and selecting YouTube videos.
    
    This cog handles the 'search' command, which allows users to search
    for songs on YouTube and select from a list of results to play.
    """
    
    def __init__(self, bot):
        """
        Initialize the SearchCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self._last_member = None
        self.config = load_config()

    async def search_youtube(self, query):
        """
        Search YouTube for videos using yt-dlp.
        
        This method uses yt-dlp to search YouTube for videos matching
        the given query and returns the top 5 results.
        
        Args:
            query (str): The search query
            
        Returns:
            list: List of video entries from YouTube search results
        """
        try:
            search_opts = {
                **BASE_YTDL_OPTIONS,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': 'ytsearch5'  # Limit to 5 results
            }
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                if 'entries' not in info:
                    return []
                return info['entries'][:5]  # Return only first 5 results
        except Exception as e:
            logging.error(f"Error searching YouTube: {str(e)}")
            return []

    @commands.command(name='search')
    async def search(self, ctx, *, query: str = None):
        """
        Search for a song on YouTube and select from results.
        
        This command searches YouTube for videos matching the query
        and presents the user with a list of results to choose from
        using reaction emojis. Once selected, the video is downloaded
        and added to the queue.
        
        Args:
            ctx: The command context
            query (str): The search query
        """
        from bot import MusicBot
        music_bot = MusicBot.get_instance(ctx.guild.id)

        # Check if a query was provided
        if not query:
            prefix = self.config['PREFIX']
            usage_embed = create_embed(
                "Usage",
                f"Usage: {prefix}search <song name/artist>\nExample: {prefix}search never gonna give you up",
                color=0xe74c3c,
                ctx=ctx
            )
            await ctx.send(embed=usage_embed)
            return

        # Only show typing during search
        results = None
        async with ctx.typing():
            results = await self.search_youtube(query)
            
        if not results:
            await ctx.send(embed=create_embed("Error", "No results found!", color=0xe74c3c, ctx=ctx))
            return

        # Create embed with search results
        embed = discord.Embed(title="Search Results", color=discord.Color.blue())
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        
        # Add each search result to the embed
        for i, entry in enumerate(results):
            title = entry.get('title', 'N/A')
            embed.add_field(
                name=f"{number_emojis[i]} {title}",
                value="\u200b",  # Zero-width space as empty value
                inline=False
            )

        embed.set_footer(text="React with 1️⃣-5️⃣ to select a song")
        message = await ctx.send(embed=embed)

        # Define check function for reaction validation
        def check(reaction, user):
            return (
                user == ctx.author 
                and str(reaction.emoji) in number_emojis[:len(results)]
                and reaction.message.id == message.id
            )

        # Create tasks for adding reactions and waiting for user input
        reaction_tasks = [
            asyncio.create_task(message.add_reaction(emoji))
            for emoji in number_emojis[:len(results)]
        ]
        wait_for_reaction = asyncio.create_task(
            self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        )

        try:
            # Start a task to delete the message after 30 seconds
            async def delete_after_timeout():
                await asyncio.sleep(30)
                try:
                    await message.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass  # Message was already deleted, we can't delete it, or other Discord error

            delete_task = asyncio.create_task(delete_after_timeout())
            
            # Wait for user reaction (other tasks will continue in parallel)
            reaction, user = await wait_for_reaction
            
            # Cancel all remaining tasks
            delete_task.cancel()
            for task in reaction_tasks:
                task.cancel()
            
            # Delete the search message with reactions
            try:
                await message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass  # Silently handle any Discord errors
            
            # Get the selected video based on the reaction
            selected_index = number_emojis.index(str(reaction.emoji))
            selected_video = results[selected_index]
            video_url = f"https://www.youtube.com/watch?v={selected_video['id']}"
            
            # Check if user is in a voice channel
            if not ctx.author.voice:
                await ctx.send(embed=create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c, ctx=ctx))
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

            # Update the music bot's voice client reference
            music_bot.voice_client = ctx.guild.voice_client
            music_bot.is_playing = False  # Reset playing state when reconnecting

            # Create processing message to show while downloading
            processing_embed = create_embed(
                "Processing",
                f"Searching for {selected_video['title']}",
                color=0x3498db,
                ctx=ctx
            )
            status_msg = await ctx.send(embed=processing_embed)

            # Download song without holding the queue lock
            result = await music_bot.download_song(video_url, status_msg=status_msg, ctx=ctx)
            if not result:
                return

            # Only lock when modifying the queue
            async with music_bot.queue_lock:
                music_bot.queue.append({
                    'title': result['title'],
                    'url': result['url'],
                    'file_path': result['file_path'],
                    'thumbnail': result.get('thumbnail'),
                    'ctx': ctx,
                    'is_stream': result.get('is_stream', False),
                    'is_from_playlist': result.get('is_from_playlist', False),
                    'requester': ctx.author
                })

                # Check if we should start playing
                should_play = not music_bot.is_playing and not music_bot.waiting_for_song and not music_bot.voice_client.is_playing()

            # These operations don't need the queue lock
            if should_play:
                # Start playing if nothing is currently playing
                await process_queue(music_bot)
            else:
                # Otherwise, add to queue and show queue position
                queue_pos = len(music_bot.queue)
                queue_embed = create_embed(
                    "Added to Queue 🎵",
                    f"[{result['title']}]({result['url']})\nPosition in queue: {queue_pos}",
                    color=0x3498db,
                    thumbnail_url=result.get('thumbnail'),
                    ctx=ctx
                )
                queue_msg = await ctx.send(embed=queue_embed)
                music_bot.queued_messages[result['url']] = queue_msg
                
        except asyncio.TimeoutError:
            # Handle timeout if user doesn't select a result
            await message.clear_reactions()
            await message.edit(content="Search timed out!", embed=None)
        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the SearchCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(SearchCog(bot))
