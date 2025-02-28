import os
import shutil
import logging
import json

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads')

def get_config():
    """
    Get configuration from config.json.
    
    Reads the AUTO_CLEAR setting from the config.json file to determine
    whether downloads should be automatically cleared.
    
    Returns:
        bool: True if auto-clear is enabled, False otherwise.
              Defaults to True if config can't be read.
    """
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            return config.get('DOWNLOADS', {}).get('AUTO_CLEAR', True)
    except Exception as e:
        logging.error(f"Error reading config.json: {str(e)}")
        return True  # Default to True if config can't be read

def clear_downloads_folder():
    """
    Clear the downloads folder if auto-clear is enabled.
    
    This function checks the configuration to see if auto-clear is enabled,
    and if so, removes all files and subdirectories from the downloads folder.
    This helps prevent the downloads folder from growing too large over time.
    
    Returns:
        None
    """
    auto_clear = get_config()
    
    if not auto_clear:
        logging.info("Auto-clear downloads is disabled, skipping cleanup")
        return

    downloads_dir = os.path.join(os.getcwd(), 'downloads')
    try:
        if os.path.exists(downloads_dir):
            for filename in os.listdir(downloads_dir):
                file_path = os.path.join(downloads_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logging.error(f"Error clearing file {file_path}: {str(e)}")
            logging.info("Downloads folder cleared successfully")
    except Exception as e:
        logging.error(f"Error clearing downloads folder: {str(e)}")