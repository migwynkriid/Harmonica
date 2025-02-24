import discord
from discord.ext import commands
import os
import json
from scripts.messages import create_embed
from scripts.config import config_vars

class ClearCache(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_confirmation = set()

    @commands.command(name='clearcache')
    async def clear_cache(self, ctx, action=None):
        """Clear the bot's cache files. Owner only command."""
        # Check if user is the owner
        if str(ctx.author.id) != str(config_vars.get('OWNER_ID')):
            await ctx.send(embed=create_embed(
                "Error",
                "This command can only be used by the bot owner.",
                color=0xe74c3c,
                ctx=ctx
            ))
            return

        if action != "confirm":
            # Add user to pending confirmation set
            self.pending_confirmation.add(ctx.author.id)
            
            # Create confirmation message with prefix
            prefix = await self.bot.get_prefix(ctx.message)
            prefix = prefix[0] if isinstance(prefix, list) else prefix
            
            await ctx.send(embed=create_embed(
                "Clear Cache Confirmation",
                f"Are you sure you want to delete the cache? This will cause the next processing to take slightly longer\n\nType **{prefix}clearcache confirm** to proceed.",
                color=0xf1c40f,
                ctx=ctx
            ))
            return

        # Check if user has pending confirmation
        if ctx.author.id not in self.pending_confirmation:
            await ctx.send(embed=create_embed(
                "Error",
                "Please use !clearcache first to initiate the cache clearing process.",
                color=0xe74c3c,
                ctx=ctx
            ))
            return

        # Remove user from pending confirmation
        self.pending_confirmation.remove(ctx.author.id)

        try:
            cache_dir = "./.cache"
            cache_files = ["blacklist.json", "filecache.json", "spotify_cache.json"]
            
            for file in cache_files:
                file_path = os.path.join(cache_dir, file)
                if os.path.exists(file_path):
                    # If it's a JSON file, clear it by writing an empty JSON object
                    with open(file_path, 'w') as f:
                        json.dump({}, f)

            await ctx.send(embed=create_embed(
                "Cache Cleared",
                "Successfully cleared all cache files.",
                color=0x2ecc71,
                ctx=ctx
            ))

        except Exception as e:
            await ctx.send(embed=create_embed(
                "Error",
                f"An error occurred while clearing the cache: {str(e)}",
                color=0xe74c3c,
                ctx=ctx
            ))

async def setup(bot):
    await bot.add_cog(ClearCache(bot))
