import asyncio
import discord
from discord.ext import tasks, commands
import subprocess
import os
from datetime import datetime
import pytz

def create_embed(title, description, color=0x3498db):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(pytz.utc)
    )
    return embed

async def check_updates(bot):
    owner = await bot.fetch_user(bot.owner_id)
    
    try:
        result = subprocess.run(
            ['pip', 'install', '--upgrade', '--dry-run', '-r', 'requirements.txt'],
            capture_output=True,
            text=True
        )
        
        if "Would install" in result.stdout:
            updates = result.stdout.split('\n')
            update_msg = '\n'.join(line for line in updates if "Would install" in line)
            
            embed = create_embed(
                "Updates available!",
                f"```\n{update_msg}\n```",
                color=0x2ecc71
            )
            embed.add_field(
                name="\u200b",
                value=f"Consider updating with `{bot.command_prefix}update` and doing a restart with `{bot.command_prefix}restart`",
                inline=False
            )
            await owner.send(embed=embed)
        
    except Exception as e:
        error_embed = create_embed(
            "Update Check Error",
            f"Error checking for updates: {str(e)}",
            color=0xe74c3c
        )
        await owner.send(embed=error_embed)

@tasks.loop(hours=1)
async def update_checker(bot):
    await check_updates(bot)

async def startup_check(bot):
    await check_updates(bot)

def setup(bot):
    update_checker.start(bot)
    bot.loop.create_task(startup_check(bot))
    bot.add_cog(UpdateScheduler(bot))
