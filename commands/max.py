import discord
from discord.ext import commands
from scripts.messages import create_embed

class MaxCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='max')
    async def max(self, ctx):
        """Play Radio Max stream"""
        from bot import MusicBot
        music_bot = MusicBot.get_instance(ctx.guild.id)
        
        try:
            play_cog = self.bot.get_cog('PlayCog')
            if play_cog:
                await play_cog.play(ctx, query='https://azuracast.novi-net.net/radio/8010/radiomax.aac')
            else:
                await ctx.send(embed=create_embed(
                    "Error",
                    "Could not find the play command. Please make sure the bot is properly set up.",
                    color=0xe74c3c,
                    ctx=ctx
                ))
        except Exception as e:
            await ctx.send(embed=create_embed(
                "Error", 
                f"An error occurred while playing Radio Max: {str(e)}", 
                color=0xe74c3c, 
                ctx=ctx
            ))

async def setup(bot):
    await bot.add_cog(MaxCog(bot))
