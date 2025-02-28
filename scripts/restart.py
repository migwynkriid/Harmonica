import os
import sys
import subprocess

def restart_bot():
    """
    Restart the bot by starting a new process and terminating the current one.
    
    This function implements a restart mechanism for the bot by spawning a new
    process running the same bot script, then terminating the current process.
    It determines the correct Python executable and script path dynamically,
    ensuring the restart works regardless of how the bot was initially started.
    
    The function uses os._exit() rather than sys.exit() to ensure an immediate
    termination without running cleanup handlers, which might interfere with
    the restart process.
    
    Returns:
        None: The function does not return as it terminates the current process
    """
    try:
        python = sys.executable
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bot.py')
        cwd = os.path.dirname(script_path)
        subprocess.Popen([python, script_path], cwd=cwd)
        os._exit(0)
    except Exception as e:
        print(f"Error during restart: {str(e)}")
        os._exit(1)