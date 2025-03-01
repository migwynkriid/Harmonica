import discord
from discord.ext import commands
from scripts.server_prefixes import set_prefix, reset_prefix, load_server_prefixes
from scripts.config import config_vars
from datetime import datetime

class PrefixCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_prefix = config_vars.get('PREFIX', '!')

    @commands.command(name="prefix", help="Change the command prefix for this server")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx, new_prefix=None):
        """
        Change the command prefix for this server.
        
        Usage:
            !prefix "new prefix" - Change the prefix to a new value
            !prefix default - Reset the prefix to the default value
        
        Args:
            new_prefix: The new prefix to set, or "default" to reset
        """
        # Set up footer for all embeds
        footer_text = f"Requested by {ctx.author.display_name}"
        footer_icon = ctx.author.display_avatar.url
        
        # If no prefix is provided, show the current prefix
        if new_prefix is None:
            current_prefix = ctx.prefix
            embed = discord.Embed(
                title="Server Prefix",
                description=f"Current prefix: `{current_prefix}`\n\n"
                            f"To change the prefix: `{current_prefix}prefix new_prefix\n`"
                            f"To reset to default: `{current_prefix}prefix default`",
                color=discord.Color.blue()
            )
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            embed.timestamp = datetime.now()
            await ctx.send(embed=embed)
            return
        
        # Handle resetting to default
        if new_prefix.lower() == "default":
            success = await reset_prefix(ctx.guild.id)
            default_prefix = config_vars.get('PREFIX', '!')
            
            if success:
                embed = discord.Embed(
                    title="Prefix Reset",
                    description=f"Server prefix has been reset to the default: `{default_prefix}`",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="Prefix Unchanged",
                    description=f"Server is already using the default prefix: `{default_prefix}`",
                    color=discord.Color.blue()
                )
            
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            embed.timestamp = datetime.now()
            await ctx.send(embed=embed)
            return
        
        # Ensure the prefix isn't too long
        if len(new_prefix) > 10:
            embed = discord.Embed(
                title="Prefix Too Long",
                description="The prefix cannot be longer than 10 characters.",
                color=discord.Color.red()
            )
            embed.set_footer(text=footer_text, icon_url=footer_icon)
            embed.timestamp = datetime.now()
            await ctx.send(embed=embed)
            return
        
        # Set the new prefix
        success = await set_prefix(ctx.guild.id, new_prefix)
        
        if success:
            embed = discord.Embed(
                title="Prefix Changed",
                description=f"Server prefix has been changed to: `{new_prefix}`\n\n"
                            f"Example: `{new_prefix}play`",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="Prefix Unchanged",
                description=f"Server is already using the prefix: `{new_prefix}`",
                color=discord.Color.blue()
            )
        
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        embed.timestamp = datetime.now()
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listen for messages that use the default prefix in a server with a custom prefix.
        
        This event handler detects when users try to use the default prefix in a server
        that has set a custom prefix, and sends a helpful message to inform them of the
        correct prefix to use.
        
        Args:
            message: The Discord message object
        """
        # Ignore messages from bots (including this bot)
        if message.author.bot:
            return
            
        # Ignore DMs
        if not message.guild:
            return
            
        # Get the default prefix
        default_prefix = self.default_prefix
        
        # Check if the message starts with the default prefix
        if not message.content.startswith(default_prefix):
            return
            
        # Check if the server has a custom prefix
        prefixes = await load_server_prefixes()
        guild_id = str(message.guild.id)
        
        # If the server doesn't have a custom prefix, or is using the default, do nothing
        if guild_id not in prefixes or prefixes[guild_id] == default_prefix:
            return
            
        # Get the custom prefix for this server
        server_prefix = prefixes[guild_id]
        
        # Check if the message is trying to use a command (default prefix + command)
        command = message.content[len(default_prefix):].split(' ')[0]
        
        # Only respond to help command or common commands
        common_commands = ['help', 'play', 'queue', 'skip', 'pause', 'resume', 'stop']
        if command.lower() not in common_commands:
            return
            
        # Create an embed to inform the user of the correct prefix
        embed = discord.Embed(
            title="Custom Prefix",
            description=f"My prefix for this server is `{server_prefix}`\n\n"
                        f"Use `{server_prefix}{command}` instead",
            color=discord.Color.blue()
        )
        
        # Add timestamp to the embed
        embed.timestamp = datetime.now()
        
        # Add footer
        footer_text = f"Requested by {message.author.display_name}"
        footer_icon = message.author.display_avatar.url
        embed.set_footer(text=footer_text, icon_url=footer_icon)
        
        # Send the message and delete it after 5 seconds
        sent_message = await message.channel.send(embed=embed)
        await sent_message.delete(delay=5)

async def setup(bot):
    await bot.add_cog(PrefixCog(bot))
