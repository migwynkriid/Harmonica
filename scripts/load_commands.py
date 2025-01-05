import os

# ANSI color codes
GREEN = '\033[92m'
BLUE = '\033[94m'
RED = '\033[91m'
RESET = '\033[0m'

async def load_commands(bot):
    """Load all commands from the commands directory."""
    print('----------------------------------------')
    print(f'{GREEN}Loading commands...{RESET}')
    commands_dir = 'commands'
    success_count = 0
    error_count = 0
    errors = []

    for filename in os.listdir(commands_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            try:
                extension_name = f'{commands_dir}.{filename[:-3]}'
                await bot.load_extension(extension_name)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f'{RED}✗ {filename}: {str(e)}{RESET}')

    # Only show errors if any occurred
    if errors:
        print('\nCommand loading errors:')
        for error in errors:
            print(error)
    
    print(f'{GREEN}Commands loaded:{RESET} {BLUE}{success_count} successful{RESET}, {RED}{error_count} failed{RESET}')
    print('----------------------------------------')
