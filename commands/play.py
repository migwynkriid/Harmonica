import discord
from discord.ext import commands
from scripts.messages import create_embed, send_queue_added_message
from scripts.permissions import check_dj_role
from scripts.process_queue import process_queue
from scripts.voice import connect_to_voice
from scripts.voice_checks import check_user_in_voice
from scripts.constants import EMBED_COLOR_ERROR, EMBED_COLOR_INFO
from scripts.playback import should_start_playback, create_song_entry

class PlayCog(commands.Cog):
    """
    Command cog for playing music in voice channels.
    
    This cog handles the 'play' command, which allows users to play music from
    YouTube, Spotify, or other supported sources in a voice channel.
    """
    
    def __init__(self, bot):
        """
        Initialize the PlayCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        from scripts.config import load_config
        self.config = load_config()

    @commands.command(name='play')
    @check_dj_role()
    async def play(self, ctx, *, query=None):
        """
        Play a song in the voice channel.
        
        This command allows users to play music from various sources including
        YouTube links, YouTube searches, and Spotify links. It handles connecting
        to voice channels, downloading songs, and managing the music queue.
        
        Args:
            ctx: The command context
            query: The search query or URL to play
        """
        from bot import MusicBot
        
        # Get server-specific music bot instance
        server_music_bot = MusicBot.get_instance(str(ctx.guild.id))
        
        # First check if user provided a query
        if not query:
            prefix = self.config['PREFIX']
            usage_embed = create_embed(
                "Error",
                f"Usage: {prefix}play YouTube Link/Youtube Search/Spotify Link",
                color=EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.send(embed=usage_embed)
            return

        # Then check if user is in a voice channel
        is_valid, error_embed = check_user_in_voice(ctx)
        if not is_valid:
            await ctx.send(embed=error_embed)
            return

        # Reset explicitly_stopped flag when play command is used
        server_music_bot.explicitly_stopped = False
        
        # Only now send the processing message
        processing_embed = create_embed(
            "Processing",
            f"Searching for {query}",
            color=EMBED_COLOR_INFO,
            ctx=ctx
        )
        status_msg = await ctx.send(embed=processing_embed)
        
        # Use the common connection utility
        if not await connect_to_voice(ctx, server_music_bot):
            error_embed = create_embed("Error", "Failed to connect to voice channel", color=EMBED_COLOR_ERROR, ctx=ctx)
            await status_msg.edit(embed=error_embed)
            return

        # Update playing state
        server_music_bot.is_playing = False  # Reset playing state when reconnecting

        # Handle Spotify links differently
        if 'open.spotify.com' in query:
            result = await server_music_bot.handle_spotify_url(query, ctx, status_msg)
            if not result:
                return
        else:
            # Download song without holding the queue lock
            result = await server_music_bot.download_song(query, status_msg=status_msg, ctx=ctx)
            if not result:
                return

            # Only lock when modifying the queue
            async with server_music_bot.queue_lock:
                # Add the song to the queue with all necessary metadata
                server_music_bot.queue.append(create_song_entry(result, ctx))

                # Check if we should start playing
                should_play = should_start_playback(server_music_bot)

            # These operations don't need the queue lock
            if should_play:
                # If nothing is playing, start playing the queue
                await process_queue(server_music_bot)
            else:
                # If something is already playing, just show the queue position
                if not result.get('is_from_playlist'):
                    await send_queue_added_message(
                        server_music_bot,
                        ctx,
                        result,
                        bot=self.bot
                    )

async def setup(bot):
    """
    Setup function to add the PlayCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(PlayCog(bot))
