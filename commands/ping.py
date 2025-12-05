import discord
from discord.ext import commands
import time
import platform
from scripts.messages import create_embed

class PingCog(commands.Cog):
    """
    Command cog for checking bot latency.
    
    This cog handles the 'ping' command, which measures and displays
    various latency metrics to assess the bot's connection quality.
    """
    
    def __init__(self, bot):
        """
        Initialize the PingCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='ping', help='Show bot latency and connection info')
    async def ping(self, ctx):
        """
        Show bot latency and connection information.
        
        This command measures and displays three types of latency:
        1. WebSocket Latency: Discord WebSocket protocol latency
        2. API Latency: Time taken for API calls to complete
        3. Message Latency: Round-trip time for sending and editing a message
        
        Args:
            ctx: The command context
        """
        # Start timing
        start_time = time.perf_counter()

        # Create initial embed
        embed = create_embed(
            "Pinging... 🏓",
            "Measuring latency...",
            color=0x3498db,
            ctx=ctx
        )
        msg = await ctx.send(embed=embed)

        # Measure Discord WebSocket protocol latency
        websocket_latency = round(self.bot.latency * 1000)  # Convert to ms

        # Measure Discord API latency (Message Round Trip)
        end_time = time.perf_counter()
        api_latency = round((end_time - start_time) * 1000)  # Convert to ms

        # Measure Message Round Trip Time
        message_latency = round((time.perf_counter() - start_time) * 1000)  # Convert to ms

        # Create detailed latency description
        description = (
            f"🌐 **WebSocket Latency:** {websocket_latency}ms\n"
            f"📡 **API Latency:** {api_latency}ms\n"
            f"💬 **Message Latency:** {message_latency}ms"
        )

        # Update embed with results
        result_embed = create_embed(
            "Pong! 🏓",
            description,
            color=0x2ecc71,  # Green color for success
            ctx=ctx
        )
        
        await msg.edit(embed=result_embed)

async def setup(bot):
    """
    Setup function to add the PingCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(PingCog(bot))
