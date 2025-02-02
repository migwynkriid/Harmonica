import discord
from discord.ext import commands
import json
import os
from scripts.messages import create_embed
from scripts.permissions import check_dj_role

class AliasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.aliases_file = 'alias.json'
        self.aliases = self.load_aliases()

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

    @commands.group(name='alias', invoke_without_command=True)
    async def alias(self, ctx):
        """Manage command aliases"""
        if ctx.invoked_subcommand is None:
            embed = create_embed(
                'Alias Commands',
                'Use these commands to manage aliases:\n'
                '`!alias add <command> <alias>` - Add an alias for a command\n'
                '`!alias remove <alias>` - Remove an alias\n'
                '`!alias list` - List all aliases',
                ctx=ctx
            )
            await ctx.send(embed=embed)

    @alias.command(name='add')
    @check_dj_role()
    async def alias_add(self, ctx, command: str = None, alias: str = None):
        """Add an alias for a command"""
        if command is None or alias is None:
            embed = create_embed('Error', 'Usage: `!alias add <command> <alias>`\nExample: `!alias add play p`', ctx=ctx)
            await ctx.send(embed=embed)
            return

        # Check if the command exists
        command = command.lower()
        alias = alias.lower()
        
        if command not in [c.name for c in self.bot.commands]:
            embed = create_embed('Error', f'Command `{command}` does not exist.', ctx=ctx)
            await ctx.send(embed=embed)
            return

        # Check if the alias is already used
        if alias in self.aliases or alias in [c.name for c in self.bot.commands]:
            embed = create_embed('Error', f'Alias `{alias}` is already in use.', ctx=ctx)
            await ctx.send(embed=embed)
            return

        # Add the alias
        self.aliases[alias] = command
        self.save_aliases()
        
        embed = create_embed('Success', f'Added alias `{alias}` for command `{command}`', ctx=ctx)
        await ctx.send(embed=embed)

    @alias.command(name='remove')
    @check_dj_role()
    async def alias_remove(self, ctx, alias: str = None):
        """Remove an alias"""
        if alias is None:
            embed = create_embed('Error', 'Usage: `!alias remove <alias>`\nExample: `!alias remove p`', ctx=ctx)
            await ctx.send(embed=embed)
            return

        alias = alias.lower()
        if alias not in self.aliases:
            embed = create_embed('Error', f'Alias `{alias}` does not exist.', ctx=ctx)
            await ctx.send(embed=embed)
            return

        command = self.aliases.pop(alias)
        self.save_aliases()
        
        embed = create_embed('Success', f'Removed alias `{alias}` for command `{command}`', ctx=ctx)
        await ctx.send(embed=embed)

    @alias.command(name='list')
    async def alias_list(self, ctx):
        """List all aliases"""
        if not self.aliases:
            embed = create_embed('Aliases', 'No aliases have been created.', ctx=ctx)
            await ctx.send(embed=embed)
            return

        alias_list = '\n'.join([f'`{alias}` → `{command}`' for alias, command in self.aliases.items()])
        embed = create_embed('Aliases', alias_list, ctx=ctx)
        await ctx.send(embed=embed)

    async def get_command(self, ctx, cmd_name: str):
        """Get the actual command from an alias"""
        cmd_name = cmd_name.lower()
        if cmd_name in self.aliases:
            return self.bot.get_command(self.aliases[cmd_name])
        return None

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.content.startswith('!'):
            return

        if message.author.bot or not message.guild:
            return

        cmd_name = message.content[1:].split()[0].lower()
        if cmd_name in self.aliases:
            ctx = await self.bot.get_context(message)
            actual_command = self.bot.get_command(self.aliases[cmd_name])
            if actual_command:
                message.content = f"!{self.aliases[cmd_name]}{message.content[len(cmd_name)+1:]}"
                ctx = await self.bot.get_context(message)
                await self.bot.invoke(ctx)

async def setup(bot):
    await bot.add_cog(AliasCog(bot))
