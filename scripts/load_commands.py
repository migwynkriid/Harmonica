import os

async def load_commands(bot):
    commands_dir = 'commands'
    print('-' * 40)
    for filename in os.listdir(commands_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            extension_name = f'{commands_dir}.{filename[:-3]}'
            try:
                await bot.load_extension(extension_name)
                # Get the command name from the filename without .py
                command_name = filename[:-3]
                print(f'Loaded: {bot.command_prefix}{command_name}')
            except Exception as e:
                print(f'Failed to load {filename}: {str(e)}')
    print('-' * 40)
