import discord
from discord.ext import commands
from scripts.cleardownloads import clear_downloads_folder
from scripts.restart import restart_bot

class Restart(commands.Cog):
    """
    Command cog for restarting the bot.
    
    This cog handles the 'restart' command, which allows the bot owner
    and authorized users to restart the bot process.
    """
    
    def __init__(self, bot):
        """
        Initialize the Restart cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.music_bot = None
        self.OWNER_ID = None
    
    def setup(self, music_bot, owner_id):
        """
        Setup the cog with music_bot instance and owner ID.
        
        Args:
            music_bot: The MusicBot instance
            owner_id: The Discord user ID of the bot owner
        """
        self.music_bot = music_bot
        self.OWNER_ID = owner_id
    
    @commands.command(name='restart')
    async def restart_cmd(self, ctx):
        """
        Restart the bot (Owner and authorized users only).
        
        This command performs the following actions:
        1. Clears the downloads folder
        2. Disconnects from any active voice channels
        3. Closes the bot connection
        4. Restarts the bot process
        
        Only the bot owner and specifically authorized users can use this command.
        
        Args:
            ctx: The command context
        """
        # Load owner ID from config if not already set
        if not isinstance(self.OWNER_ID, int):
            with open('config.json', 'r') as f:
                import json
                config = json.load(f)
                self.OWNER_ID = int(config['OWNER_ID'])
        
        # Check if user is authorized to restart the bot
        allowed_users = [self.OWNER_ID, 740974326873849886]
        if ctx.author.id not in allowed_users:
            await ctx.send(embed=discord.Embed(title="Error", description="You are not authorized to use this command!", color=0xe74c3c))
            return

        # Send restart notification
        await ctx.send(embed=discord.Embed(title="Restarting", description="Bot is restarting...", color=0xf1c40f))
        
        try:
            # Clean up before restarting
            clear_downloads_folder()
            if self.music_bot and self.music_bot.voice_client:
                await self.music_bot.voice_client.disconnect()        
            await self.bot.close()
            restart_bot()
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="Error", description=f"Failed to restart: {str(e)}", color=0xe74c3c))

async def setup(bot):
    """
    Setup function to add the Restart cog to the bot.
    
    Args:
        bot: The bot instance
        
    Returns:
        Restart: The initialized Restart cog instance
    """
    restart = Restart(bot)
    
    # Get owner ID from config
    try:
        with open('config.json', 'r') as f:
            import json
            config = json.load(f)
            owner_id = int(config['OWNER_ID'])
    except Exception as e:
        print(f"Error loading owner ID from config: {e}")
        owner_id = None
    
    # Initialize the cog
    restart.setup(None, owner_id)  # music_bot will be set later
    await bot.add_cog(restart)
    return restart
