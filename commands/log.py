import discord
from discord.ext import commands
import json
import os

class Log(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.json', 'r') as f:
            config = json.load(f)
        self.OWNER_ID = int(config['OWNER_ID'])

    def read_last_lines(self, filename, max_lines=1000):
        """Read the last N lines of a file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                f.seek(0, 2)  # Seek to end of file
                file_size = f.tell()
                
                lines = []
                chunk_size = 8192
                position = file_size
                
                while len(lines) < max_lines and position > 0:
                    chunk_pos = max(position - chunk_size, 0)
                    f.seek(chunk_pos)
                    
                    if chunk_pos > 0:
                        f.readline()
                        
                    chunk_lines = f.read(position - chunk_pos).splitlines()
                    lines = chunk_lines + lines
                    position = chunk_pos
                    
                    if len(lines) > max_lines:
                        lines = lines[-max_lines:]
                
                return lines
        except FileNotFoundError:
            return []
        except Exception as e:
            return [f"Error reading file: {str(e)}"]

    @commands.command(name='log')
    @commands.is_owner()
    async def log(self, ctx):
        """Send the last 1000 lines of both log files - Owner only command"""
        if ctx.author.id != self.OWNER_ID:
            await ctx.send(embed=discord.Embed(
                title="Error",
                description="This command is only available to the bot owner.",
                color=0xe74c3c
            ))
            return
            
        try:
            # Read both log files
            system_log_lines = self.read_last_lines('log.txt')
            command_log_lines = self.read_last_lines('commandlog.txt')
            
            # Create temporary files for both logs
            if system_log_lines:
                with open('temp_system_log.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(system_log_lines))
                await ctx.send("System Log:", file=discord.File('temp_system_log.txt'))
                os.remove('temp_system_log.txt')
            
            if command_log_lines:
                with open('temp_command_log.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(command_log_lines))
                await ctx.send("Command Log:", file=discord.File('temp_command_log.txt'))
                os.remove('temp_command_log.txt')
                
            if not system_log_lines and not command_log_lines:
                await ctx.send("No log files found.")
            
        except Exception as e:
            await ctx.send(f"Error processing log files: {str(e)}")

async def setup(bot):
    await bot.add_cog(Log(bot))
