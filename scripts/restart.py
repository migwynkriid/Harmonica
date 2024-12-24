import os
import sys
import subprocess

def restart_bot():
    """Restart the bot by starting a new process and terminating the current one"""
    try:
        python = sys.executable
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bot.py')
        cwd = os.path.dirname(script_path)
        subprocess.Popen([python, script_path], cwd=cwd)
        os._exit(0)
    except Exception as e:
        print(f"Error during restart: {str(e)}")
        os._exit(1)