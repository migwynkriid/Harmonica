import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.queueclear import clear_queue_command
from scripts.voice_checks import check_voice_state

class ClearCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='clear', aliases=['clearqueue'])
    @check_dj_role()
    async def clear(self, ctx, position: int = None):
        """Clear the queue or remove a specific song"""
        from bot import music_bot

        try:
            # Check voice state
            is_valid, error_embed = await check_voice_state(ctx, music_bot)
            if not is_valid:
                await ctx.send(embed=error_embed)
                return

            await clear_queue_command(ctx, music_bot, position)

        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"An error occurred while clearing: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(ClearCog(bot))
