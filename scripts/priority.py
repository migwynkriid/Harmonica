import os
import sys
import psutil
import logging

# Windows HIGH_PRIORITY_CLASS value
WINDOWS_HIGH_PRIORITY_VALUE = 128

# Define HIGH_PRIORITY_CLASS constant for Windows
# On Windows, this is defined in psutil, but we define it here for compatibility
if sys.platform == 'win32' and hasattr(psutil, 'HIGH_PRIORITY_CLASS'):
    HIGH_PRIORITY_CLASS = psutil.HIGH_PRIORITY_CLASS
else:
    HIGH_PRIORITY_CLASS = WINDOWS_HIGH_PRIORITY_VALUE

def set_high_priority():
    """
    Set high priority for the current process on Windows only.
    
    This function attempts to elevate the process priority of the bot
    to improve performance, particularly for audio processing tasks.
    It only works on Windows systems and sets the process to HIGH_PRIORITY_CLASS,
    which is the highest priority that can be set without administrator privileges.
    
    The function logs the priority change if successful, or logs an error
    if the operation fails.
    
    Returns:
        bool: True if priority was successfully changed, False otherwise
    """
    # Skip if not Windows
    if not sys.platform == 'win32':
        logging.info("Priority setting skipped - Windows only feature")
        return False

    try:
        process = psutil.Process(os.getpid())
        current_priority = process.nice()
        process.nice(HIGH_PRIORITY_CLASS)
        new_priority = process.nice()
        logging.info(f"Windows priority changed: {current_priority} (default) -> {new_priority} (high)")
        logging.info("Successfully set to HIGH_PRIORITY_CLASS (highest without admin)")
        return True
    except Exception as e:
        logging.error(f"Error setting Windows process priority: {str(e)}")
        return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    set_high_priority()