from discord.ext import commands
import discord
import json

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)
OWNER_ID = config['OWNER_ID']

async def setup(bot):
    bot.add_command(logclear)
    return None

@commands.command(name='logclear')
@commands.is_owner()
async def logclear(ctx):
    """Clear the log file - Owner only command"""
    if ctx.author.id != OWNER_ID:
        await ctx.send(embed=discord.Embed(title="Error", description="This command is only available to the bot owner.", color=0xe74c3c))
        return

    try:
        # Clear the log file
        with open('log.txt', 'w', encoding='utf-8') as f:
            f.write('---')
        
        await ctx.send(embed=discord.Embed(title="Success", description="Log file has been cleared.", color=0x2ecc71))
        print("Log file cleared by owner")
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"Failed to clear log file: {str(e)}", color=0xe74c3c))