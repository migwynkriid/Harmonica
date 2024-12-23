import os

async def load_commands(bot):
    commands_dir = 'commands'
    print('-' * 40)
    for filename in os.listdir(commands_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            extension_name = f'{commands_dir}.{filename[:-3]}'
            try:
                await bot.load_extension(extension_name)
                print(f'Successfully loaded extension: {extension_name}')
            except Exception as e:
                print(f'Failed to load extension {extension_name}: {str(e)}')
    print('-' * 40)
