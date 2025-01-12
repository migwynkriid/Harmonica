from discord.ext import commands
import discord

async def setup(bot):
    bot.add_command(servers)
    return None

@commands.command(name='servers')
@commands.is_owner()
async def servers(ctx):
    """Shows all servers the bot is in (Owner only)"""
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
