import os

# ANSI color codes
GREEN = '\033[92m'
BLUE = '\033[94m'
RED = '\033[91m'
RESET = '\033[0m'

def load_scripts():
    """
    Load all scripts from the scripts directory.
    
    This function scans the scripts directory and counts all Python files
    that could be loaded as modules. Unlike load_commands, this function
    doesn't actually import the modules, but rather serves as a verification
    that the script files exist and are properly named.
    
    Returns:
        None: The function prints loading results to the console
    """
    print('----------------------------------------')
    print(f'{GREEN}Loading scripts...{RESET}')
    script_dir = 'scripts'
    
    script_count = sum(
        1 for filename in os.listdir(script_dir)
        if filename.endswith('.py') and not filename.startswith('_')
    )
    
    print(f'{GREEN}Scripts loaded:{RESET} {BLUE}{script_count} found{RESET}')
