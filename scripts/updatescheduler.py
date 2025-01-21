import asyncio
import discord
from discord.ext import tasks, commands
import subprocess
import os
import sys
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
    try:
        owner = await bot.fetch_user(bot.owner_id)
    except discord.NotFound:
        print("\033[91mWarning: Could not send update notification. Owner could not be contacted.\nDo you share a server with the bot?\033[0m")
        return
    except Exception as e:
        print(f"\033[91mWarning: Could not send update notification. Error: {str(e)}\033[0m")
        return
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', '--dry-run', '--pre', '-r', 'requirements.txt', '--break-system-packages'],
            capture_output=True,
            text=True
        )
        
        if "Would install" in result.stdout:
            updates = result.stdout.split('\n')
            update_msg = '\n'.join(line for line in updates if "Would install" in line)
            
            # Check if bot is in voice chat
            from bot import music_bot
            is_in_voice = music_bot and music_bot.voice_client and music_bot.voice_client.is_connected()
            
            if not is_in_voice:
                # Automatically update and restart if not in voice chat
                try:
                    # Run actual update command
                    subprocess.run(
                        [sys.executable, '-m', 'pip', 'install', '--upgrade', '--pre', '-r', 'requirements.txt', '--break-system-packages'],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    
                    # Import and call restart function
                    from scripts.restart import restart_bot
                    restart_bot()
                except Exception as e:
                    error_embed = create_embed(
                        "Auto-Update Error",
                        f"Failed to auto-update: {str(e)}",
                        color=0xe74c3c
                    )
                    await owner.send(embed=error_embed)
            else:
                # Just notify owner about updates if in voice chat
                embed = create_embed(
                    "Updates available!",
                    f"```\n{update_msg}\n```",
                    color=0x2ecc71
                )
                embed.add_field(
                    name="\u200b",
                    value=f"Bot is currently in a voice chat.\nPlease update manually with `{bot.command_prefix}update` and restart with `{bot.command_prefix}restart` when convenient.",
                    inline=False
                )
                await owner.send(embed=embed)
        
    except Exception as e:
        error_embed = create_embed(
            "Update Check Error",
            f"Error checking for updates: {str(e)}",
            color=0xe74c3c
        )
        try:
            await owner.send(embed=error_embed)
        except:
            print(f"\033[91mWarning: Could not send update error notification to owner.\033[0m")

@tasks.loop(hours=1)
async def update_checker(bot):
    await check_updates(bot)

async def startup_check(bot):
    await check_updates(bot)

def setup(bot):
    update_checker.start(bot)
    bot.loop.create_task(startup_check(bot))
    bot.add_cog(UpdateScheduler(bot))
