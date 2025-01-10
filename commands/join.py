import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role

class JoinCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='join', aliases=['summon'])
    @check_dj_role()
    async def join(self, ctx):
        """Join the user's voice channel"""
        from bot import music_bot

        # Check if user is in a voice channel
        if not ctx.author.voice:
            await ctx.send(embed=create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c, ctx=ctx))
            return

        # Connect to voice channel if needed
        if not ctx.guild.voice_client:
            try:
                await ctx.author.voice.channel.connect()
            except discord.ClientException as e:
                if "already connected" in str(e):
                    # If already connected but in a different state, clean up and reconnect
                    if music_bot.voice_client:
                        await music_bot.voice_client.disconnect()
                    music_bot.voice_client = None
                    await ctx.author.voice.channel.connect()
                else:
                    raise e
        elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
            await ctx.guild.voice_client.move_to(ctx.author.voice.channel)

        music_bot.voice_client = ctx.guild.voice_client

async def setup(bot):
    await bot.add_cog(JoinCog(bot))
