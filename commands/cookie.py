import os
import discord
import shutil
from discord.ext import commands
from scripts.config import load_config
from scripts.messages import create_embed
from scripts.paths import get_root_dir
from pathlib import Path

class CookieCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.owner_id = self.config.get('OWNER_ID')
        self.prefix = self.config.get('PREFIX', '!')  # Get the prefix from config
        self.root_dir = get_root_dir()
        
    @commands.command(name="cookie", aliases=["cookies"])
    async def cookie(self, ctx):
        """
        Upload a cookies.txt file for the bot to use with YouTube-DL.
        This command can only be used by the bot owner.
        
        The cookies.txt file allows the bot to access age-restricted content
        and premium content that requires authentication.
        
        Usage:
            {prefix}cookie (with an attached cookies.txt file)
            
        To get a cookies.txt file:
        1. Install the "Get cookies.txt" browser extension
        2. Log in to YouTube/Google
        3. Use the extension to export cookies
        4. Attach the file to your message with this command
        """
        # Get the server-specific prefix if available
        prefix = ctx.prefix if hasattr(ctx, 'prefix') and ctx.prefix else self.prefix
        
        # Check if the user is the bot owner
        if str(ctx.author.id) != str(self.owner_id):
            await ctx.send(
                embed=create_embed(
                    "Error",
                    "Only the bot owner can use this command.",
                    color=0xe74c3c,
                    ctx=ctx
                )
            )
            return
        
        # If no attachments, check if we want to display cookie status
        if not ctx.message.attachments:
            cookie_path = Path(os.path.join(self.root_dir, "cookies.txt"))
            if cookie_path.exists():
                # Get file size and modification time
                size_bytes = cookie_path.stat().st_size
                size_kb = size_bytes / 1024
                mod_time = cookie_path.stat().st_mtime
                
                import datetime
                mod_date = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                
                await ctx.send(
                    embed=create_embed(
                        "Cookies Status",
                        f"A cookies.txt file is currently installed.\n\n"
                        f"**File Size:** {size_kb:.2f} KB\n"
                        f"**Last Modified:** {mod_date}\n\n"
                        f"To update the file, attach a new cookies.txt file to your message with the {prefix}cookie command.",
                        color=0x3498db,
                        ctx=ctx
                    )
                )
            else:
                await ctx.send(
                    embed=create_embed(
                        "Cookies Status",
                        "No cookies.txt file is currently installed.\n\n"
                        f"To install a cookies file, attach a cookies.txt file to your message with the {prefix}cookie command.\n\n"
                        "**Why use cookies?**\n"
                        "- Access age-restricted content\n"
                        "- Access premium content\n"
                        "- Avoid some YouTube restrictions\n\n"
                        "**How to get cookies.txt:**\n"
                        "1. Install the 'Get cookies.txt' browser extension\n"
                        "2. Log in to YouTube/Google\n"
                        "3. Use the extension to export cookies\n"
                        f"4. Attach the file to your message with this command",
                        color=0xf39c12,
                        ctx=ctx
                    )
                )
            return
        
        # Get the first attachment
        attachment = ctx.message.attachments[0]
        
        # Check if the file is named cookies.txt
        if not attachment.filename.lower() == "cookies.txt":
            await ctx.send(
                embed=create_embed(
                    "Error",
                    "The attached file must be named 'cookies.txt'.",
                    color=0xe74c3c,
                    ctx=ctx
                )
            )
            return
        
        # Define the path to save the file
        cookies_path = os.path.join(self.root_dir, "cookies.txt")
        
        # Create a backup of the existing file if it exists
        if os.path.exists(cookies_path):
            try:
                backup_path = os.path.join(self.root_dir, "cookies.txt.backup")
                shutil.copy2(cookies_path, backup_path)
            except Exception as e:
                print(f"Failed to create backup of cookies.txt: {str(e)}")
        
        try:
            # Download the file
            await attachment.save(cookies_path)
            
            # Check if the file was saved successfully
            if os.path.exists(cookies_path):
                # Get file size
                size_bytes = os.path.getsize(cookies_path)
                size_kb = size_bytes / 1024
                
                # Check permissions before attempting to delete
                can_delete = ctx.channel.permissions_for(ctx.guild.me).manage_messages
                
                if can_delete:
                    try:
                        await ctx.message.delete()
                        # No need to send a separate message about deletion
                    except Exception as e:
                        print(f"Failed to delete message despite having permissions: {str(e)}")
                else:
                    # Don't attempt to delete if we know we don't have permissions
                    print(f"Bot lacks manage_messages permission in channel {ctx.channel.name}")
                
                # Send success message without mentioning deletion
                await ctx.send(
                    embed=create_embed(
                        "Success",
                        f"The cookies.txt file has been uploaded and saved successfully.\n\n"
                        f"**File Size:** {size_kb:.2f} KB\n\n"
                        f"The bot will now use these cookies for YouTube requests. "
                        f"This will allow access to age-restricted and premium content.",
                        color=0x2ecc71,
                        ctx=ctx
                    )
                )
            else:
                await ctx.send(
                    embed=create_embed(
                        "Error",
                        "Failed to save the cookies.txt file.",
                        color=0xe74c3c,
                        ctx=ctx
                    )
                )
        except Exception as e:
            await ctx.send(
                embed=create_embed(
                    "Error",
                    f"An error occurred while saving the file: {str(e)}",
                    color=0xe74c3c,
                    ctx=ctx
                )
            )
            
            # Restore backup if it exists
            backup_path = os.path.join(self.root_dir, "cookies.txt.backup")
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, cookies_path)
                    await ctx.send(
                        embed=create_embed(
                            "Recovery",
                            "Previous cookies.txt file has been restored from backup.",
                            color=0xf39c12,
                            ctx=ctx
                        )
                    )
                except Exception as e:
                    print(f"Failed to restore cookies.txt from backup: {str(e)}")

async def setup(bot):
    await bot.add_cog(CookieCommand(bot)) 