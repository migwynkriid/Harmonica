import discord
from discord.ext import commands
from scripts.config import load_config
import logging
from datetime import datetime, timezone, timedelta

class HelpCog(commands.Cog):
    """
    Command cog for displaying help information.
    
    This cog handles the 'help' command, which provides users with
    information about all available commands organized by category.
    """
    
    def __init__(self, bot):
        """
        Initialize the HelpCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.config = load_config()

    @commands.command(name='help')
    async def help_command(self, ctx):
        """
        Send an embedded message with all commands and explanations.
        
        This command displays all available commands organized into categories:
        - Music Commands: Commands related to music playback
        - Voice & Search Commands: Commands for voice channel management and search
        - Admin Commands: Owner-only commands for bot management
        
        Args:
            ctx: The command context
        """
        prefix = self.config['PREFIX']
        
        # Create embeds for different categories
        music_embed = discord.Embed(title="Help - Music Commands", description="Music playback related commands:", color=0x3498db)
        music_embed.timestamp = datetime.now()
        
        # Music playback commands
        music_embed.add_field(name=f"{prefix}play [URL/search term]", value="Play a song from YouTube or Spotify.", inline=True)
        music_embed.add_field(name=f"{prefix}pause", value="Pause the current song.", inline=True)
        music_embed.add_field(name=f"{prefix}resume", value="Resume playback.", inline=True)
        music_embed.add_field(name=f"{prefix}stop", value="Stop playback, clear the queue, and leave the voice channel.", inline=True)
        music_embed.add_field(name=f"{prefix}skip", value="Skip the current song.", inline=True)
        music_embed.add_field(name=f"{prefix}replay", value="Restart the current song.", inline=True)
        music_embed.add_field(name=f"{prefix}queue", value="Show the current song queue.", inline=True)
        music_embed.add_field(name=f"{prefix}clear", value="Clears the queue", inline=True)
        music_embed.add_field(name=f"{prefix}shuffle", value="Shuffle the queue.", inline=True)
        music_embed.add_field(name=f"{prefix}loop", value="Toggle loop mode for the current song.", inline=True)
        music_embed.add_field(name=f"{prefix}nowplaying", value="Show the currently playing song.", inline=True)
        music_embed.add_field(name=f"{prefix}lyrics", value="Get lyrics for the current song", inline=True)
        
        # Voice and Search commands embed
        voice_embed = discord.Embed(title="Help - Voice & Search Commands", description="Voice channel and search related commands:", color=0x3498db)
        voice_embed.timestamp = datetime.now()
        
        voice_embed.add_field(name=f"{prefix}join", value="Join a voice channel.", inline=True)
        voice_embed.add_field(name=f"{prefix}leave", value="Leave the voice channel.", inline=True)
        voice_embed.add_field(name=f"{prefix}search", value="Searches for a song on YouTube.", inline=True)
        voice_embed.add_field(name=f"{prefix}random", value="Searches for a random song on YouTube.", inline=True)
        voice_embed.add_field(name=f"{prefix}randomradio", value="Play a random radio station.", inline=True)
        voice_embed.add_field(name=f"{prefix}max", value="Play Radio Max stream.", inline=True)
        voice_embed.add_field(name=f"{prefix}ping", value="Show bot latency and connection info.", inline=True)
        voice_embed.add_field(name=f"{prefix}alias", value="Manage aliases", inline=True)
        
        # Admin commands embed (Owner Only)
        user_id = str(ctx.author.id)
        owner_id = str(self.config['OWNER_ID'])
        
        logging.info(f"User ID: {user_id}, Owner ID: {owner_id}")
        
        # Set footer for all embeds
        footer_text = f"Requested by {ctx.author.display_name}"
        footer_icon = ctx.author.display_avatar.url
        
        music_embed.set_footer(text=footer_text, icon_url=footer_icon)
        voice_embed.set_footer(text=footer_text, icon_url=footer_icon)
        
        # Send the category embeds
        await ctx.send(embed=music_embed)
        await ctx.send(embed=voice_embed)
        
        # Send admin commands embed only to the owner
        if user_id == owner_id and owner_id != "YOUR_DISCORD_USER_ID":
            admin_embed = discord.Embed(title="Help - Admin Commands", description="Owner only commands:", color=0x3498db)
            admin_embed.timestamp = datetime.now()
            
            admin_embed.add_field(name=f"{prefix}log", value="Show the log file (Owner Only).", inline=True)
            admin_embed.add_field(name=f"{prefix}clearcache", value="Initiates the clear cache process (Owner Only).", inline=True)
            admin_embed.add_field(name=f"{prefix}logclear", value="Clear the log file (Owner Only).", inline=True)
            admin_embed.add_field(name=f"{prefix}version", value="Check the version of yt-dlp and commit info (Owner Only).", inline=True)
            admin_embed.add_field(name=f"{prefix}update", value="Updates the yt-dlp executable and does a git pull (Owner Only).", inline=True)
            admin_embed.add_field(name=f"{prefix}restart", value="Restart the bot (Owner Only).", inline=True)
            
            admin_embed.set_footer(text=footer_text, icon_url=footer_icon)
            await ctx.send(embed=admin_embed)

async def setup(bot):
    """
    Setup function to add the HelpCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(HelpCog(bot))
