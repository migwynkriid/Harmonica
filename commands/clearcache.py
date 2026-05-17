from discord.ext import commands
import os
from scripts.messages import create_embed
from scripts.config import config_vars
from scripts.constants import EMBED_COLOR_ERROR, EMBED_COLOR_SUCCESS, EMBED_COLOR_WARNING

class ClearCache(commands.Cog):
    """
    Command cog for clearing the bot's cache files.
    
    This cog provides the 'clearcache' command, which allows the bot owner
    to clear various cache files used by the bot, such as blacklist, file cache,
    and Spotify cache.
    """
    
    def __init__(self, bot):
        """
        Initialize the ClearCache cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.pending_confirmation = set()

    @commands.command(name='clearcache')
    async def clear_cache(self, ctx, action=None):
        """
        Clear the bot's cache files. Owner only command.
        
        This command clears various cache files used by the bot, including
        blacklist, file cache, and Spotify cache. It requires confirmation
        to prevent accidental cache clearing.
        
        Args:
            ctx: The command context
            action: Optional action parameter, 'confirm' to confirm cache clearing
        """
        # Check if user is the owner
        if str(ctx.author.id) != str(config_vars.get('OWNER_ID')):
            await ctx.send(embed=create_embed(
                "Error",
                "This command can only be used by the bot owner.",
                color=EMBED_COLOR_ERROR,
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
                color=EMBED_COLOR_WARNING,
                ctx=ctx
            ))
            return

        # Check if user has pending confirmation
        if ctx.author.id not in self.pending_confirmation:
            await ctx.send(embed=create_embed(
                "Error",
                "Please use !clearcache first to initiate the cache clearing process.",
                color=EMBED_COLOR_ERROR,
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
                color=EMBED_COLOR_SUCCESS,
                ctx=ctx
            ))

        except Exception as e:
            await ctx.send(embed=create_embed(
                "Error",
                f"An error occurred while clearing the cache: {str(e)}",
                color=EMBED_COLOR_ERROR,
                ctx=ctx
            ))

async def setup(bot):
    """
    Setup function to add the ClearCache cog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(ClearCache(bot))
