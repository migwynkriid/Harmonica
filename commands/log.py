import discord
from discord.ext import commands
import json

class Log(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.json', 'r') as f:
            config = json.load(f)
        self.owner_id = config['OWNER_ID']

    @commands.command(name='log')
    @commands.is_owner()
    async def log(self, ctx):
        """Clear the log file - Owner only command"""
        if ctx.author.id != self.owner_id:
            await ctx.send(embed=discord.Embed(
                title="Error",
                description="This command is only available to the bot owner.",
                color=0xe74c3c
            ))
            return
            
        try:
            await ctx.send(file=discord.File('log.txt'))
        except Exception as e:
            await ctx.send(f"Error uploading log file: {str(e)}")

async def setup(bot):
    await bot.add_cog(Log(bot))
