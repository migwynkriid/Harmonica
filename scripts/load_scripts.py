import os

def load_scripts():
    scripts_dir = 'scripts'
    print('-' * 40)
    for filename in os.listdir(scripts_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            script_name = filename[:-3]
            try:
                print(f'Loaded: {script_name}')
            except Exception as e:
                print(f'Failed to load {filename}: {str(e)}')
    print('-' * 40)
