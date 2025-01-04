import discord
from discord.ext import commands
import time
from scripts.messages import create_embed
from scripts.process_queue import process_queue

class PlayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='play')
    async def play(self, ctx, *, query=None):
        """Play a song in the voice channel"""
        from __main__ import music_bot
        
        # First check if user provided a query
        if not query:
            usage_embed = create_embed(
                "Usage",
                "Usage: !play YouTube Link/Youtube Search/Spotify Link",
                color=0xe74c3c,
                ctx=ctx
            )
            await ctx.send(embed=usage_embed)
            return

        # Then check if user is in a voice channel
        if not ctx.author.voice:
            embed = create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c, ctx=ctx)
            await ctx.send(embed=embed)
            return

        # Only now send the processing message
        processing_embed = create_embed(
            "Processing",
            f"Searching for {query}",
            color=0x3498db,
            ctx=ctx
        )
        status_msg = await ctx.send(embed=processing_embed)
        
        # Connect to voice channel if needed
        if not ctx.guild.voice_client:
            await ctx.author.voice.channel.connect()
        elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
            await ctx.guild.voice_client.move_to(ctx.author.voice.channel)

        music_bot.voice_client = ctx.guild.voice_client

        if 'open.spotify.com' in query:
            result = await music_bot.handle_spotify_url(query, ctx, status_msg)
            if not result:
                return
        else:
            async with music_bot.queue_lock:
                result = await music_bot.download_song(query, status_msg=status_msg, ctx=ctx)
                if not result:
                    return

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

                if not music_bot.is_playing and not music_bot.waiting_for_song and not music_bot.voice_client.is_playing():
                    await process_queue(music_bot)
                else:
                    if not result.get('is_from_playlist'):
                        queue_pos = len(music_bot.queue)
                        # Check if current song is looped from the Loop cog
                        loop_cog = self.bot.get_cog('Loop')
                        description = f"[🎵 {result['title']}]({result['url']})"
                        
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
                            thumbnail_url=result.get('thumbnail'),
                            ctx=ctx
                        )
                        queue_msg = await ctx.send(embed=queue_embed)
                        music_bot.queued_messages[result['url']] = queue_msg

async def setup(bot):
    await bot.add_cog(PlayCog(bot))
