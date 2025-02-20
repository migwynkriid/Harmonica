import os
import sys
import psutil
import logging

def set_high_priority():
    """Set high priority for the current process on Windows only."""
    # Skip if not Windows
    if not sys.platform == 'win32':
        logging.info("Priority setting skipped - Windows only feature")
        return False

    try:
        process = psutil.Process(os.getpid())
        current_priority = process.nice()
        process.nice(psutil.HIGH_PRIORITY_CLASS)
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