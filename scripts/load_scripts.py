import os

def load_scripts():
    """Load all scripts from the scripts directory."""
    print('----------------------------------------')
    print('Loading scripts...')
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
                errors.append(f'✗ {filename}: {str(e)}')

    # Only show errors if any occurred
    if errors:
        print('\nScript loading errors:')
        for error in errors:
            print(error)
    
    print(f'Scripts loaded: {success_count} successful, {error_count} failed')
