import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import asyncio

class BruhCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.bruh_url = "https://www.myinstants.com/media/sounds/movie_1.mp3"
        self.is_playing_bruh = False

    @commands.command(name='bruh')
    @commands.cooldown(1, 3.0, commands.BucketType.guild)
    async def bruh(self, ctx):
        """Play the bruh sound effect"""
        try:
            if not ctx.voice_client:
                # Not in a voice channel
                embed = discord.Embed(title="Error", description="I'm not in a voice channel!", color=discord.Color.red())
                await ctx.send(embed=embed)
                return

            # Store current audio settings
            current_source = None
            was_playing = False
            if ctx.voice_client.is_playing():
                current_source = ctx.voice_client.source
                was_playing = True
                ctx.voice_client.pause()

            # Create audio source for bruh sound
            audio = FFmpegPCMAudio(
                self.bruh_url,
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                options='-vn -filter:a volume=2'
            )
            
            # Play bruh sound
            ctx.voice_client.play(audio, after=lambda e: asyncio.run_coroutine_threadsafe(self._after_bruh(ctx, current_source, was_playing), self.bot.loop))
            self.is_playing_bruh = True
            
        except Exception as e:
            if was_playing and current_source:
                ctx.voice_client.play(current_source)
            embed = discord.Embed(title="Error", description=f"An error occurred: {str(e)}", color=discord.Color.red())
            await ctx.send(embed=embed)

    async def _after_bruh(self, ctx, previous_source, was_playing):
        """Callback after bruh sound finishes"""
        self.is_playing_bruh = False
        if was_playing and previous_source and ctx.voice_client:
            ctx.voice_client.play(previous_source)

    @bruh.error
    async def bruh_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            return  # Silently ignore cooldown errors
        # Handle other errors normally
        embed = discord.Embed(title="Error", description=f"An error occurred: {str(error)}", color=discord.Color.red())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BruhCog(bot))
