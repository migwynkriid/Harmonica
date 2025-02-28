import discord
from discord.ext import commands
import json
import os
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.config import load_config

class AliasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.aliases_file = 'aliases.json'
        self.aliases = self.load_aliases()
        self.config = load_config()

    def load_aliases(self):
        """Load aliases from the JSON file"""
        if os.path.exists(self.aliases_file):
            try:
                with open(self.aliases_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_aliases(self):
        """Save aliases to the JSON file"""
        with open(self.aliases_file, 'w') as f:
            json.dump(self.aliases, f, indent=4)

    def get_server_aliases(self, guild_id):
        """Get aliases for a specific server"""
        guild_id = str(guild_id)  # Convert to string for JSON compatibility
        if guild_id not in self.aliases:
            self.aliases[guild_id] = {}
        return self.aliases[guild_id]

    @commands.group(name='alias', invoke_without_command=True)
    async def alias(self, ctx):
        """Manage command aliases"""
        if ctx.invoked_subcommand is None:
            prefix = self.config['PREFIX']
            embed = create_embed(
                'Alias Commands',
                'Use these commands to manage aliases:\n'
                f'\n`{prefix}alias add <command> <alias>` - Add an alias for a command\n'
                f'`{prefix}alias remove <alias>` - Remove an alias\n'
                f'`{prefix}alias list` - List all aliases',
                ctx=ctx
            )
            await ctx.send(embed=embed)

    @alias.command(name='add')
    @check_dj_role()
    async def alias_add(self, ctx, command: str = None, alias: str = None):
        """Add an alias for a command"""
        prefix = self.config['PREFIX']
        if command is None or alias is None:
            embed = create_embed('Error', f'Usage: `{prefix}alias add <command> <alias>`\nExample: `{prefix}alias add play p`', ctx=ctx)
            await ctx.send(embed=embed)
            return

        # Check if the command exists
        command = command.lower()
        alias = alias.lower()
        
        if command not in [c.name for c in self.bot.commands]:
            embed = create_embed('Error', f'Command `{command}` does not exist.', ctx=ctx)
            await ctx.send(embed=embed)
            return

        # Get server-specific aliases
        server_aliases = self.get_server_aliases(ctx.guild.id)

        # Check if the alias is already used
        if alias in server_aliases or alias in [c.name for c in self.bot.commands]:
            embed = create_embed('Error', f'Alias `{alias}` is already in use.', ctx=ctx)
            await ctx.send(embed=embed)
            return

        # Add the alias
        server_aliases[alias] = command
        self.save_aliases()
        
        embed = create_embed('Success', f'Added alias `{alias}` for command `{command}`', ctx=ctx)
        await ctx.send(embed=embed)

    @alias.command(name='remove')
    @check_dj_role()
    async def alias_remove(self, ctx, alias: str = None):
        """Remove an alias"""
        prefix = self.config['PREFIX']
        if alias is None:
            embed = create_embed('Error', f'Usage: `{prefix}alias remove <alias>`\nExample: `{prefix}alias remove p`', ctx=ctx)
            await ctx.send(embed=embed)
            return

        alias = alias.lower()
        server_aliases = self.get_server_aliases(ctx.guild.id)
        
        if alias not in server_aliases:
            embed = create_embed('Error', f'Alias `{alias}` does not exist.', ctx=ctx)
            await ctx.send(embed=embed)
            return

        command = server_aliases.pop(alias)
        self.save_aliases()
        
        embed = create_embed('Success', f'Removed alias `{alias}` for command `{command}`', ctx=ctx)
        await ctx.send(embed=embed)

    @alias.command(name='list')
    async def alias_list(self, ctx):
        """List all aliases"""
        server_aliases = self.get_server_aliases(ctx.guild.id)
        
        if not server_aliases:
            embed = create_embed('Aliases', 'No aliases have been created for this server.', ctx=ctx)
            await ctx.send(embed=embed)
            return

        # Group aliases by their commands
        command_groups = {}
        for alias, command in server_aliases.items():
            if command not in command_groups:
                command_groups[command] = []
            command_groups[command].append(alias)

        # Format each command group
        prefix = self.config['PREFIX']
        formatted_groups = []
        for command, aliases in sorted(command_groups.items()):
            aliases.sort()  # Sort aliases alphabetically
            # Add configured prefix to both command and aliases
            formatted_groups.append(f'`{prefix}{command}` > {", ".join(f"`{prefix}{alias}`" for alias in aliases)}')

        alias_list = '\n'.join(formatted_groups)
        embed = create_embed('Aliases', alias_list, ctx=ctx)
        await ctx.send(embed=embed)

    async def get_command(self, ctx, cmd_name: str):
        """Get the actual command from an alias"""
        cmd_name = cmd_name.lower()
        server_aliases = self.get_server_aliases(ctx.guild.id)
        
        if cmd_name in server_aliases:
            return self.bot.get_command(server_aliases[cmd_name])
        return None

    @commands.Cog.listener()
    async def on_message(self, message):
        prefix = self.config['PREFIX']
        if not message.content.startswith(prefix):
            return

        if message.author.bot or not message.guild:
            return

        # Handle empty prefix case
        content_after_prefix = message.content[len(prefix):]
        if not content_after_prefix.strip():  # If there's nothing after the prefix
            return

        cmd_name = content_after_prefix.split()[0].lower()
        server_aliases = self.get_server_aliases(message.guild.id)
        
        if cmd_name in server_aliases:
            ctx = await self.bot.get_context(message)
            actual_command = self.bot.get_command(server_aliases[cmd_name])
            if actual_command:
                message.content = f"{prefix}{server_aliases[cmd_name]}{message.content[len(cmd_name)+len(prefix):]}"
                ctx = await self.bot.get_context(message)
                await self.bot.invoke(ctx)

async def setup(bot):
    await bot.add_cog(AliasCog(bot))
