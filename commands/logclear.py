from discord.ext import commands
import discord
from scripts.constants import EMBED_COLOR_ERROR, EMBED_COLOR_SUCCESS


async def setup(bot):
    """
    Setup function to add the logclear command to the bot.
    
    Args:
        bot: The bot instance
    """
    bot.add_command(logclear)
    return None


@commands.command(name='logclear')
@commands.is_owner()
async def logclear(ctx):
    """
    Clear the log file.
    
    This command clears the contents of the main log file by overwriting it
    with a minimal placeholder. This helps manage log file size and cleanup.
    This command is restricted to the bot owner only.
    
    Args:
        ctx: The command context
    """
    try:
        # Clear the log file
        with open('log.txt', 'w', encoding='utf-8') as f:
            f.write('---')
        
        await ctx.send(embed=discord.Embed(title="Success", description="Log file has been cleared.", color=EMBED_COLOR_SUCCESS))
        print("Log file cleared by owner")
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"Failed to clear log file: {str(e)}", color=EMBED_COLOR_ERROR))