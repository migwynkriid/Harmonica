import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice import connect_to_voice

class JoinCog(commands.Cog):
    """
    Command cog for joining voice channels.
    
    This cog handles the 'join' command, which allows users to make
    the bot join their current voice channel.
    """
    
    def __init__(self, bot):
        """
        Initialize the JoinCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='join', aliases=['summon'])
    @check_dj_role()
    async def join(self, ctx):
        """
        Join the user's voice channel.
        
        This command makes the bot join the voice channel that the user
        is currently in. If the bot is already in a different voice channel,
        it will move to the user's channel.
        
        Args:
            ctx: The command context
        """
        from bot import MusicBot
        
        # Get server-specific music bot instance
        server_music_bot = MusicBot.get_instance(str(ctx.guild.id))

        # Check if user is in a voice channel
        if not ctx.author.voice:
            await ctx.send(embed=create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c, ctx=ctx))
            return

        # Use the common connection utility
        if await connect_to_voice(ctx, server_music_bot):
            await ctx.send(embed=create_embed("Joined", "Successfully joined your voice channel", color=0x3498db, ctx=ctx))
        else:
            await ctx.send(embed=create_embed("Error", "Failed to join voice channel", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the JoinCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(JoinCog(bot))
