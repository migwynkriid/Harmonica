import os
import discord
from discord.ext.commands import ExtensionAlreadyLoaded

# ANSI color codes
GREEN = '\033[92m'
BLUE = '\033[94m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

async def load_commands(bot):
    """
    Load all commands from the commands directory.
    
    This function dynamically loads all Python files in the commands directory
    as Discord bot extensions. It tracks successful and failed loads and
    provides a summary of the loading process.
    
    If a command is already loaded, it will be skipped instead of showing an error.
    
    Args:
        bot: The Discord bot instance to load commands into
        
    Returns:
        None: The function prints loading results to the console
    """
    print('----------------------------------------')
    print(f'{GREEN}Loading commands...{RESET}')
    commands_dir = 'commands'
    success_count = 0
    error_count = 0
    skipped_count = 0
    errors = []
    
    # Check if this is a reconnection by seeing if any commands are already loaded
    is_reconnection = False
    for filename in os.listdir(commands_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            extension_name = f'{commands_dir}.{filename[:-3]}'
            if extension_name in bot.extensions:
                is_reconnection = True
                break
    
    if is_reconnection:
        print(f'{YELLOW}Reconnection detected - skipping already loaded commands{RESET}')
        # Just return without trying to load commands again
        print(f'{GREEN}Commands loaded:{RESET} {BLUE}0 successful{RESET}, {RED}0 failed{RESET}, {YELLOW}all skipped (reconnection){RESET}')
        print('----------------------------------------')
        return

    for filename in os.listdir(commands_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            extension_name = f'{commands_dir}.{filename[:-3]}'
            try:
                # Check if the extension is already loaded
                if extension_name in bot.extensions:
                    skipped_count += 1
                    continue
                
                await bot.load_extension(extension_name)
                success_count += 1
            except ExtensionAlreadyLoaded:
                # Skip already loaded extensions without counting as an error
                skipped_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f'{RED}✗ {filename}: {str(e)}{RESET}')

    # Only show errors if any occurred
    if errors:
        print('\nCommand loading errors:')
        for error in errors:
            print(error)
    
    print(f'{GREEN}Commands loaded:{RESET} {BLUE}{success_count} successful{RESET}, {RED}{error_count} failed{RESET}, {YELLOW}{skipped_count} skipped{RESET}')
    print('----------------------------------------')
