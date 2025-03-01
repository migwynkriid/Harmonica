import json
import os
import asyncio

# Path to the server prefixes JSON file
SERVER_PREFIXES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server_prefixes.json')

# Lock for thread-safe file operations
_file_lock = asyncio.Lock()

async def load_server_prefixes():
    """
    Load server prefixes from the JSON file.
    
    Returns:
        dict: A dictionary mapping guild IDs to their custom prefixes
    """
    async with _file_lock:
        if not os.path.exists(SERVER_PREFIXES_FILE):
            # Create empty file if it doesn't exist
            await save_server_prefixes({})
            return {}
        
        try:
            with open(SERVER_PREFIXES_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # If the file is corrupted, create a new empty one
            await save_server_prefixes({})
            return {}

async def save_server_prefixes(prefixes):
    """
    Save server prefixes to the JSON file.
    
    Args:
        prefixes (dict): A dictionary mapping guild IDs to their custom prefixes
    """
    async with _file_lock:
        with open(SERVER_PREFIXES_FILE, 'w') as f:
            json.dump(prefixes, f, indent=4)

async def get_prefix(bot, message):
    """
    Get the prefix for a specific guild.
    
    This function is designed to be used as a command_prefix function for discord.py.
    It returns the custom prefix for the guild if one exists, otherwise it returns
    the default prefix from the config.
    
    Args:
        bot: The Discord bot instance
        message: The Discord message object
        
    Returns:
        str: The prefix for the guild
    """
    # If DM channel, use default prefix
    if message.guild is None:
        from scripts.config import config_vars
        return config_vars.get('PREFIX', '!')
    
    prefixes = await load_server_prefixes()
    guild_id = str(message.guild.id)  # Convert to string for JSON compatibility
    
    # Return custom prefix if it exists, otherwise return default prefix
    if guild_id in prefixes:
        return prefixes[guild_id]
    else:
        from scripts.config import config_vars
        return config_vars.get('PREFIX', '!')

async def set_prefix(guild_id, new_prefix):
    """
    Set a custom prefix for a specific guild.
    
    Args:
        guild_id: The ID of the guild
        new_prefix: The new prefix to set
        
    Returns:
        bool: True if the prefix was changed, False if it was the same
    """
    guild_id = str(guild_id)  # Convert to string for JSON compatibility
    prefixes = await load_server_prefixes()
    
    # Check if the prefix is already set to the same value
    if guild_id in prefixes and prefixes[guild_id] == new_prefix:
        return False
    
    # Update the prefix
    prefixes[guild_id] = new_prefix
    await save_server_prefixes(prefixes)
    return True

async def reset_prefix(guild_id):
    """
    Reset a guild's prefix to the default.
    
    Args:
        guild_id: The ID of the guild
        
    Returns:
        bool: True if the prefix was reset, False if it was already default
    """
    guild_id = str(guild_id)  # Convert to string for JSON compatibility
    prefixes = await load_server_prefixes()
    
    # Check if the guild has a custom prefix
    if guild_id not in prefixes:
        return False
    
    # Remove the custom prefix
    del prefixes[guild_id]
    await save_server_prefixes(prefixes)
    return True
