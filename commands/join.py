import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role

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
        self._last_member = None

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

        # Connect to voice channel if needed
        if not ctx.guild.voice_client:
            try:
                # Bot is not in any voice channel, connect to user's channel with self_deaf=True
                await ctx.author.voice.channel.connect(self_deaf=True)
            except discord.ClientException as e:
                if "already connected" in str(e):
                    # If already connected but in a different state, clean up and reconnect
                    if server_music_bot.voice_client:
                        await server_music_bot.voice_client.disconnect()
                    server_music_bot.voice_client = None
                    await ctx.author.voice.channel.connect(self_deaf=True)
                else:
                    raise e
        elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
            # Bot is in a different voice channel, move to user's channel
            await ctx.guild.voice_client.move_to(ctx.author.voice.channel)
            # Ensure self_deaf is set to True after moving
            await ctx.guild.voice_client.edit(self_deaf=True)

        # Update the server music bot's voice client reference
        server_music_bot.voice_client = ctx.guild.voice_client
        
        await ctx.send(embed=create_embed("Joined", "Successfully joined your voice channel", color=0x3498db, ctx=ctx))

async def setup(bot):
    """
    Setup function to add the JoinCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(JoinCog(bot))
