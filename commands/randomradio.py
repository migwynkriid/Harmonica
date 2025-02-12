from discord.ext import commands
from scripts.messages import create_embed
import aiohttp
import random

class RandomRadioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.api_base = "https://de1.api.radio-browser.info/json/stations"

    async def get_random_station(self, retry_count=0):
        """Fetch a random radio station from the Radio Browser API"""
        async with aiohttp.ClientSession() as session:
            # Adjust parameters based on retry count
            params = {
                'hidebroken': 'true',  # Only working stations
                'has_extended_info': 'true',  # Stations with complete info
                'limit': 5,  # Get multiple stations in case some fail
                'order': 'random'  # Random order from the API
            }
            
            # First try: High quality stations with random offset
            if retry_count == 0:
                params.update({
                    'offset': random.randint(0, 1000),
                    'bitrateMin': 64
                })
            # Second try: Any quality stations with random offset
            elif retry_count == 1:
                params.update({
                    'offset': random.randint(0, 1000)
                })
            # Last try: Get more stations without quality filters
            else:
                params.update({
                    'limit': 20
                })
            
            async with session.get(f"{self.api_base}/search", params=params) as response:
                if response.status == 200:
                    stations = await response.json()
                    # Filter stations with valid URLs and shuffle them
                    valid_stations = [s for s in stations if s.get('url_resolved')]
                    if valid_stations:
                        random.shuffle(valid_stations)  # Extra randomization
                        return valid_stations[0]  # Return the first valid station
                    elif retry_count < 2:  # Try again with different parameters
                        return await self.get_random_station(retry_count + 1)
        return None

    async def try_play_station(self, ctx, station, status_msg):
        """Try to play a radio station and handle potential errors"""
        try:
            # Get the bot instance
            from bot import music_bot
            
            # Check if user is in a voice channel
            if not ctx.author.voice:
                await status_msg.edit(embed=create_embed(
                    "Error",
                    "You must be in a voice channel to use this command!",
                    color=0xe74c3c,
                    ctx=ctx
                ))
                return False

            # Connect to voice channel if needed
            if not ctx.guild.voice_client:
                try:
                    await ctx.author.voice.channel.connect()
                except Exception as e:
                    print(f"Error connecting to voice channel: {str(e)}")
                    await status_msg.edit(embed=create_embed(
                        "Error",
                        "Failed to connect to voice channel. Please try again.",
                        color=0xe74c3c,
                        ctx=ctx
                    ))
                    return False
            elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
                await ctx.guild.voice_client.move_to(ctx.author.voice.channel)

            # Set up voice client
            music_bot.voice_client = ctx.guild.voice_client
            
            # Try to play the station
            result = {
                'title': station['name'],
                'url': station['url_resolved'],
                'file_path': station['url_resolved'],
                'is_stream': True,
                'thumbnail': station.get('favicon')
            }
            
            # Add to queue with correct title and favicon from the API
            async with music_bot.queue_lock:
                music_bot.queue.append({
                    **result,
                    'ctx': ctx,
                    'is_from_playlist': False,
                    'requester': ctx.author
                })
                
                # Check if we should start playing
                should_play = not music_bot.is_playing and music_bot.voice_client and not music_bot.voice_client.is_playing()
            
            if should_play:
                from scripts.process_queue import process_queue
                await process_queue(music_bot)
            
            # Delete status message after 5 seconds
            await status_msg.delete(delay=5)
            return True
            
        except Exception as e:
            error_str = str(e)
            if "HTTP Error 416" in error_str:
                return False
            print(f"Error in try_play_station: {str(e)}")
            return False

    @commands.command(name='randomradio')
    async def randomradio(self, ctx):
        """Play a random radio station from Radio Browser"""
        # Check if user is in voice chat
        if not ctx.author.voice:
            await ctx.send(embed=create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c, ctx=ctx))
            return
            
        # Check if bot is in same voice chat
        if ctx.voice_client and ctx.author.voice.channel != ctx.voice_client.channel:
            await ctx.send(embed=create_embed("Error", "You must be in the same voice channel as the bot to use this command!", color=0xe74c3c, ctx=ctx))
            return

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Send initial status message
                status_msg = await ctx.send(embed=create_embed(
                    "Random Radio",
                    "Fetching a random radio station...",
                    color=0x3498db,
                    ctx=ctx
                ))

                # Get a random station
                station = await self.get_random_station()
                if not station:
                    await status_msg.edit(embed=create_embed(
                        "Error",
                        "Could not find any available radio stations after multiple attempts. The radio service might be experiencing issues. Please try again in a moment.",
                        color=0xe74c3c,
                        ctx=ctx
                    ))
                    return

                # Update status message with station info
                await status_msg.edit(embed=create_embed(
                    "Random Radio",
                    f"Found station: {station['name']}\nTags: {', '.join(station.get('tags', '').split(',')[:3]) if station.get('tags') else 'No tags'}\nCountry: {station.get('country', 'Unknown')}\n\nStarting playback...",
                    color=0x3498db,
                    ctx=ctx
                ))

                # Try to play the station
                if await self.try_play_station(ctx, station, status_msg):
                    return
                
                # If we get here, there was an HTTP 416 error, try again
                retry_count += 1
                if retry_count < max_retries:
                    await status_msg.edit(embed=create_embed(
                        "Random Radio",
                        "That station didn't work, trying another one...",
                        color=0x3498db,
                        ctx=ctx
                    ))
                await status_msg.delete(delay=5)

            except Exception as e:
                await ctx.send(embed=create_embed(
                    "Error",
                    f"An error occurred while fetching a random radio station: {str(e)}",
                    color=0xe74c3c,
                    ctx=ctx
                ))
                return
        
        # If we've exhausted all retries
        await ctx.send(embed=create_embed(
            "Error",
            "Could not find a working radio station after several attempts. Please try again later.",
            color=0xe74c3c,
            ctx=ctx
        ))

async def setup(bot):
    await bot.add_cog(RandomRadioCog(bot))
