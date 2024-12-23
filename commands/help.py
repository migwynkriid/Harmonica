import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help')
    async def help_command(self, ctx):
        """Send an embedded message with all commands and explanations"""
        help_embed = discord.Embed(title="Help - Commands", description="List of available commands:", color=0x3498db)
        help_embed.add_field(name="!play [URL/search term]", value="Play a song from YouTube or Spotify.", inline=False)
        help_embed.add_field(name="!pause", value="Pause the current song.", inline=False)
        help_embed.add_field(name="!resume", value="Resume playback.", inline=False)
        help_embed.add_field(name="!skip", value="Skip the current song.", inline=False)
        help_embed.add_field(name="!queue", value="Show the current song queue.", inline=False)
        help_embed.add_field(name="!leave", value="Leave the voice channel.", inline=False)
        help_embed.add_field(name="!loop", value="Toggle loop mode for the current song.", inline=False)
        help_embed.add_field(name="!stop", value="Stop playback, clear the queue, and leave the voice channel.", inline=False)
        help_embed.add_field(name="!logclear", value="Clear the log file (Owner Only).", inline=False)
        help_embed.add_field(name="!nowplaying", value="Show the currently playing song.", inline=False)
        help_embed.add_field(name="!version", value="Check the version of yt-dlp and commit info. (Owner Only)", inline=False)
        help_embed.add_field(name="!update", value="Updates the yt-dlp executable. (Owner Only)", inline=False)
        await ctx.send(embed=help_embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
