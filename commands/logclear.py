from discord.ext import commands
import discord
from scripts.config import load_config

# Load config once at module level
_config = load_config()
OWNER_ID = int(_config['OWNER_ID'])

async def setup(bot):
    bot.add_command(logclear)
    return None

@commands.command(name='logclear')
@commands.is_owner()
async def logclear(ctx):
    """Clear the log file - Owner only command"""
    try:
        # Clear the log file
        with open('log.txt', 'w', encoding='utf-8') as f:
            f.write('---')
        
        await ctx.send(embed=discord.Embed(title="Success", description="Log file has been cleared.", color=0x2ecc71))
        print("Log file cleared by owner")
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"Failed to clear log file: {str(e)}", color=0xe74c3c))