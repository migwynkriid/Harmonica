import discord
from discord.ext import commands
import json

class Log(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.json', 'r') as f:
            config = json.load(f)
        self.OWNER_ID = int(config['OWNER_ID'])

    @commands.command(name='log')
    @commands.is_owner()
    async def log(self, ctx):
        """Send the last 1000 lines of the log file - Owner only command"""
        if ctx.author.id != self.OWNER_ID:
            await ctx.send(embed=discord.Embed(
                title="Error",
                description="This command is only available to the bot owner.",
                color=0xe74c3c
            ))
            return
            
        try:
            # Read the last 1000 lines of the log file
            with open('log.txt', 'r', encoding='utf-8') as f:
                # Seek to the end of file
                f.seek(0, 2)
                # Get total file size
                file_size = f.tell()
                
                lines = []
                # Start from the end and read chunks backwards
                chunk_size = 8192
                position = file_size
                
                while len(lines) < 1000 and position > 0:
                    # Move back one chunk or to start of file
                    chunk_pos = max(position - chunk_size, 0)
                    f.seek(chunk_pos)
                    
                    # If not at start, discard partial line
                    if chunk_pos > 0:
                        f.readline()
                        
                    # Add lines to our list, but only up to 1000
                    chunk_lines = f.read(position - chunk_pos).splitlines()
                    lines = chunk_lines + lines
                    position = chunk_pos
                    
                    if len(lines) > 1000:
                        lines = lines[-1000:]

            # Write the last 1000 lines to a temporary file
            temp_log = 'temp_log.txt'
            with open(temp_log, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            # Send the temporary file
            await ctx.send(file=discord.File(temp_log))
            
            # Clean up the temporary file
            import os
            os.remove(temp_log)
            
        except Exception as e:
            await ctx.send(f"Error processing log file: {str(e)}")

async def setup(bot):
    await bot.add_cog(Log(bot))
