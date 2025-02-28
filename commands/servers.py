from discord.ext import commands
import discord

async def setup(bot):
    """
    Setup function to add the servers command to the bot.
    
    Args:
        bot: The bot instance
    """
    bot.add_command(servers)
    return None

@commands.command(name='servers')
@commands.is_owner()
async def servers(ctx):
    """
    Shows all servers the bot is in (Owner only).
    
    This command displays a list of all servers (guilds) that the bot
    is currently a member of, including server IDs and member counts.
    This command is restricted to the bot owner only.
    
    Args:
        ctx: The command context
    """
    guilds = ctx.bot.guilds
    
    # Create an embed with server information
    embed = discord.Embed(
        title="Bot Server List", 
        description=f"Currently in {len(guilds)} servers:", 
        color=0x3498db
    )
    
    # Add each server to the embed
    for guild in guilds:
        member_count = len(guild.members)
        embed.add_field(
            name=guild.name,
            value=f"ID: {guild.id}\nMembers: {member_count}",
            inline=False
        )
    
    await ctx.send(embed=embed)
