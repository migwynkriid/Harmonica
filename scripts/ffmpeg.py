import sys
import subprocess

def check_ffmpeg_in_path():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_ffmpeg_windows():
    try:
        print("FFmpeg not found. Installing FFmpeg using winget...")
        subprocess.run(['winget', 'install', 'FFmpeg (Essentials Build)'], check=True)
        print("FFmpeg installed successfully. Please restart the bot for changes to take effect.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing FFmpeg: {e}")
        return False

def install_ffmpeg_macos():
    try:
        print("FFmpeg not found. Attempting to install FFmpeg using Homebrew...")
        try:
            subprocess.run(['brew', 'install', 'ffmpeg'], check=True)
            print("FFmpeg installed successfully using Homebrew. Please restart the bot for changes to take effect.")
            return True
        except subprocess.CalledProcessError:
            print("Homebrew installation failed. Trying MacPorts...")
            try:
                subprocess.run(['sudo', 'port', 'install', 'ffmpeg'], check=True)
                print("FFmpeg installed successfully using MacPorts. Please restart the bot for changes to take effect.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"MacPorts installation failed: {e}")
                return False
    except Exception as e:
        print(f"Error installing FFmpeg: {e}")
        return False

def install_ffmpeg_linux():
    try:
        print("FFmpeg not found. Installing FFmpeg using apt...")
        subprocess.run(['sudo', 'apt', 'install', 'ffmpeg', '-y'], check=True)
        print("FFmpeg installed successfully. Please restart the bot for changes to take effect.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing FFmpeg: {e}")
        return False

def get_ffmpeg_path():
    if sys.platform.startswith('win'):
        if check_ffmpeg_in_path():
            return 'ffmpeg'
        
        if install_ffmpeg_windows():
            return 'ffmpeg'
        else:
            print("WARNING: FFmpeg not found and installation failed. Please install FFmpeg manually.")
            return 'ffmpeg'

    elif sys.platform.startswith('darwin'):
        if check_ffmpeg_in_path():
            return 'ffmpeg'
        
        if install_ffmpeg_macos():
            return 'ffmpeg'
        else:
            print("WARNING: FFmpeg not found and installation failed. Please install FFmpeg manually using 'brew install ffmpeg' or 'sudo port install ffmpeg'")
            return 'ffmpeg'
    else:
        if check_ffmpeg_in_path():
            return 'ffmpeg'
        
        if install_ffmpeg_linux():
            return 'ffmpeg'
        else:
            print("WARNING: FFmpeg not found and installation failed. Please install FFmpeg manually using 'sudo apt install ffmpeg'")
            return 'ffmpeg'