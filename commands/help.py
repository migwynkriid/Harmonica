import discord
from discord.ext import commands
from scripts.config import load_config
import logging
from datetime import datetime, timezone, timedelta

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()

    @commands.command(name='help')
    async def help_command(self, ctx):
        """Send an embedded message with all commands and explanations"""
        prefix = self.config['PREFIX']
        help_embed = discord.Embed(title="Help - Commands", description="List of available commands:", color=0x3498db)
        help_embed.timestamp = datetime.now()
        
        # Music playback commands
        help_embed.add_field(name=f"{prefix}play [URL/search term]", value="Play a song from YouTube or Spotify.", inline=True)
        help_embed.add_field(name=f"{prefix}pause", value="Pause the current song.", inline=True)
        help_embed.add_field(name=f"{prefix}resume", value="Resume playback.", inline=True)
        help_embed.add_field(name=f"{prefix}stop", value="Stop playback, clear the queue, and leave the voice channel.", inline=True)
        help_embed.add_field(name=f"{prefix}skip", value="Skip the current song.", inline=True)
        help_embed.add_field(name=f"{prefix}replay", value="Restart the current song.", inline=True)
        help_embed.add_field(name=f"{prefix}queue", value="Show the current song queue.", inline=True)
        help_embed.add_field(name=f"{prefix}clear", value="Clears the queue", inline=True)
        help_embed.add_field(name=f"{prefix}shuffle", value="Shuffle the queue.", inline=True)
        help_embed.add_field(name=f"{prefix}loop", value="Toggle loop mode for the current song.", inline=True)
        help_embed.add_field(name=f"{prefix}nowplaying", value="Show the currently playing song.", inline=True)
        help_embed.add_field(name=f"{prefix}lyrics", value="Get lyrics for the current song", inline=True)
        
        # Voice and Search commands
        help_embed.add_field(name=f"{prefix}join", value="Join a voice channel.", inline=True)
        help_embed.add_field(name=f"{prefix}leave", value="Leave the voice channel.", inline=True)
        help_embed.add_field(name=f"{prefix}search", value="Searches for a song on YouTube.", inline=True)
        help_embed.add_field(name=f"{prefix}random", value="Searches for a random song on YouTube.", inline=True)
        help_embed.add_field(name=f"{prefix}randomradio", value="Play a random radio station.", inline=True)
        help_embed.add_field(name=f"{prefix}max", value="Play Radio Max stream.", inline=True)
        
        # Utility commands
        help_embed.add_field(name=f"{prefix}ping", value="Show bot latency and connection info.", inline=True)
        help_embed.add_field(name=f"{prefix}alias", value="Manage aliases", inline=True)
        
        # Admin commands (Owner Only)
        user_id = str(ctx.author.id)
        owner_id = str(self.config['OWNER_ID'])
        
        logging.info(f"User ID: {user_id}, Owner ID: {owner_id}")
        
        if user_id == owner_id and owner_id != "YOUR_DISCORD_USER_ID":
            help_embed.add_field(name=f"{prefix}log", value="Show the log file (Owner Only).", inline=True)
            help_embed.add_field(name=f"{prefix}clearcache", value="Initiates the clear cache process (Owner Only).", inline=True)
            help_embed.add_field(name=f"{prefix}logclear", value="Clear the log file (Owner Only).", inline=True)
            help_embed.add_field(name=f"{prefix}version", value="Check the version of yt-dlp and commit info (Owner Only).", inline=True)
            help_embed.add_field(name=f"{prefix}update", value="Updates the yt-dlp executable and does a git pull (Owner Only).", inline=True)
            help_embed.add_field(name=f"{prefix}restart", value="Restart the bot (Owner Only).", inline=True)
        
        help_embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=help_embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
