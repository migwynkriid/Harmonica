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
    success_count = 0
    error_count = 0
    errors = []

    for filename in os.listdir(script_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            script_name = filename[:-3]
            try:
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f'{RED}✗ {filename}: {str(e)}{RESET}')

    # Only show errors if any occurred
    if errors:
        print('\nScript loading errors:')
        for error in errors:
            print(error)
    
    print(f'{GREEN}Scripts loaded:{RESET} {BLUE}{success_count} successful{RESET}, {RED}{error_count} failed{RESET}')
