"""
Configuration management for the Discord Music Bot.
"""
import os
import json

def load_config():
    """Load or create the configuration file."""
    default_config = {
        "OWNER_ID": "YOUR_DISCORD_USER_ID",
        "PREFIX": "!",
        "LOG_LEVEL": "INFO",
        "VOICE": {
            "INACTIVITY_TIMEOUT": 60,
            "AUTO_LEAVE_EMPTY": True,
            "DEFAULT_VOLUME": 100
        },
        "DOWNLOADS": {
            "AUTO_CLEAR": True
        },
        "MESSAGES": {
            "SHOW_PROGRESS_BAR": True
        }
    }

    # Create default config if it doesn't exist
    if not os.path.exists('config.json'):
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=4)

    # Load the config
    with open('config.json', 'r') as f:
        config = json.load(f)
        return {
            'OWNER_ID': config['OWNER_ID'],
            'PREFIX': config['PREFIX'],
            'LOG_LEVEL': config.get('LOG_LEVEL', 'INFO'),
            'INACTIVITY_TIMEOUT': config.get('VOICE', {}).get('INACTIVITY_TIMEOUT', 60),
            'AUTO_LEAVE_EMPTY': config.get('VOICE', {}).get('AUTO_LEAVE_EMPTY', True),
            'DEFAULT_VOLUME': config.get('VOICE', {}).get('DEFAULT_VOLUME', 100),
            'AUTO_CLEAR_DOWNLOADS': config.get('DOWNLOADS', {}).get('AUTO_CLEAR', True),
            'SHOW_PROGRESS_BAR': config.get('MESSAGES', {}).get('SHOW_PROGRESS_BAR', True)
        }
