import os

# ANSI color codes
GREEN = '\033[92m'
BLUE = '\033[94m'
RESET = '\033[0m'

def load_scripts():
    """
    Validate that all scripts in the scripts directory exist.
    Actual script importing happens via Python's normal import mechanism.
    """
    print('----------------------------------------')
    print(f'{GREEN}Validating scripts...{RESET}')
    script_dir = 'scripts'
    script_count = 0

    for filename in os.listdir(script_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            script_count += 1

    print(f'{GREEN}Scripts validated:{RESET} {BLUE}{script_count} files{RESET}')
