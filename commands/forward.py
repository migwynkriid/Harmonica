import discord
from discord.ext import commands
from scripts.messages import create_embed
from scripts.permissions import check_dj_role
from scripts.voice_checks import check_voice_state
from scripts.seek import seek_audio


class ForwardCog(commands.Cog):
    """
    Command cog for seeking forward in the current song.
    
    This cog provides the 'forward' command, which allows users to skip
    forward by a specified number of seconds in the currently playing song.
    """
    
    def __init__(self, bot):
        """
        Initialize the ForwardCog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    @commands.command(name='forward', aliases=['ff', 'fastforward', 'fw'])
    @check_dj_role()
    async def forward(self, ctx, seconds: int = 10):
        """
        Skip forward in the currently playing song by a specified number of seconds.
        
        This command allows users to seek forward in the currently playing song.
        The default skip amount is 10 seconds if not specified.
        This command requires DJ permissions.
        
        Usage: !forward [seconds]
        
        Args:
            ctx: The command context
            seconds (int): Number of seconds to skip forward (default: 10)
        """
        from bot import MusicBot
        
        try:
            # Validate seconds parameter
            if seconds <= 0:
                await ctx.send(embed=create_embed(
                    "Error", 
                    "Forward amount must be greater than 0 seconds!", 
                    color=0xe74c3c, 
                    ctx=ctx
                ))
                return
                
            # Get server-specific music bot instance
            music_bot = MusicBot.get_instance(str(ctx.guild.id))
            
            # Check voice state (user must be in same voice channel as bot)
            is_valid, error_embed = await check_voice_state(ctx, music_bot)
            if not is_valid:
                await ctx.send(embed=error_embed)
                return

            # Perform the seek operation
            success, message, new_position = await seek_audio(ctx, music_bot, seconds, direction="forward")
            
            if not success:
                await ctx.send(embed=create_embed("Error", message, color=0xe74c3c, ctx=ctx))
                return
            
            # Send success message
            current_song = music_bot.current_song
            embed = create_embed(
                "⏩ Fast Forward",
                f"Skipped forward {seconds} seconds to {message}\n[{current_song['title']}]({current_song['url']})",
                color=0x3498db,
                ctx=ctx
            )
            if 'thumbnail' in current_song:
                embed.set_thumbnail(url=current_song['thumbnail'])
            await ctx.send(embed=embed)

        except ValueError:
            await ctx.send(embed=create_embed(
                "Error", 
                "Invalid number of seconds! Please provide a valid integer.", 
                color=0xe74c3c, 
                ctx=ctx
            ))
        except Exception as e:
            await ctx.send(embed=create_embed(
                "Error", 
                f"An error occurred while seeking forward: {str(e)}", 
                color=0xe74c3c, 
                ctx=ctx
            ))


async def setup(bot):
    """
    Setup function to add the ForwardCog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(ForwardCog(bot))
