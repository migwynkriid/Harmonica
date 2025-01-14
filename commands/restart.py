import discord
from discord.ext import commands
from scripts.cleardownloads import clear_downloads_folder
from scripts.restart import restart_bot

class Restart(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_bot = None
        self.OWNER_ID = None
    
    def setup(self, music_bot, owner_id):
        """Setup the cog with music_bot instance and owner ID"""
        self.music_bot = music_bot
        self.OWNER_ID = owner_id
    
    @commands.command(name='restart')
    async def restart_cmd(self, ctx):
        """Restart the bot (Owner and authorized users only)"""
        if not isinstance(self.OWNER_ID, int):
            with open('config.json', 'r') as f:
                import json
                config = json.load(f)
                self.OWNER_ID = int(config['OWNER_ID'])
        
        allowed_users = [self.OWNER_ID, 740974326873849886]
        if ctx.author.id not in allowed_users:
            await ctx.send(embed=discord.Embed(title="Error", description="You are not authorized to use this command!", color=0xe74c3c))
            return

        await ctx.send(embed=discord.Embed(title="Restarting", description="Bot is restarting...", color=0xf1c40f))
        
        try:
            clear_downloads_folder()
            if self.music_bot and self.music_bot.voice_client:
                await self.music_bot.voice_client.disconnect()        
            await self.bot.close()
            restart_bot()
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="Error", description=f"Failed to restart: {str(e)}", color=0xe74c3c))

async def setup(bot):
    """Setup the cog"""
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
