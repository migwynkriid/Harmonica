import discord
from discord.ext import commands
import os
import tempfile
from scripts.config import load_config


class Log(commands.Cog):
    """
    Command cog for retrieving bot log files.
    
    This cog handles the 'log' command, which allows the bot owner
    to view the most recent log entries from the bot's log files.
    """
    
    def __init__(self, bot):
        """
        Initialize the Log cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot

    def read_last_lines(self, filename, max_lines=1000):
        """
        Read the last N lines of a file.
        
        This method efficiently reads the last specified number of lines
        from a file without loading the entire file into memory.
        
        Args:
            filename (str): The path to the file to read
            max_lines (int): Maximum number of lines to read
            
        Returns:
            list: The last N lines of the file as a list of strings
        """
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
        """
        Send the last 1000 lines of both log files.
        
        This command retrieves the last 1000 lines from both the system log
        and command log files, and sends them as text file attachments.
        This command is restricted to the bot owner only.
        
        Args:
            ctx: The command context
        """
        temp_files = []
        try:
            # Read both log files
            system_log_lines = self.read_last_lines('log.txt')
            command_log_lines = self.read_last_lines('commandlog.txt')
            
            # Create and send temporary files for both logs using unique temp files
            if system_log_lines:
                with tempfile.NamedTemporaryFile(mode='w', suffix='_system_log.txt', 
                                                  delete=False, encoding='utf-8') as f:
                    f.write('\n'.join(system_log_lines))
                    temp_files.append(f.name)
                await ctx.send("System Log:", file=discord.File(temp_files[-1], filename='system_log.txt'))
            
            if command_log_lines:
                with tempfile.NamedTemporaryFile(mode='w', suffix='_command_log.txt', 
                                                  delete=False, encoding='utf-8') as f:
                    f.write('\n'.join(command_log_lines))
                    temp_files.append(f.name)
                await ctx.send("Command Log:", file=discord.File(temp_files[-1], filename='command_log.txt'))
                
            if not system_log_lines and not command_log_lines:
                await ctx.send("No log files found.")
            
        except Exception as e:
            await ctx.send(f"Error processing log files: {str(e)}")
        finally:
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

async def setup(bot):
    """
    Setup function to add the Log cog to the bot.
    
    Args:
        bot: The bot instance
    """
    await bot.add_cog(Log(bot))
