import os

async def load_commands(bot):
    """Load all commands from the commands directory."""
    print('----------------------------------------')
    print('Loading commands...')
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
                errors.append(f'✗ {filename}: {str(e)}')

    # Only show errors if any occurred
    if errors:
        print('\nCommand loading errors:')
        for error in errors:
            print(error)
    
    print(f'Commands loaded: {success_count} successful, {error_count} failed')
    print('----------------------------------------')
