"""
Path management for external executables.
"""
import os
import platform

def _is_executable(path):
    """Check if a file exists and is executable."""
    return os.path.isfile(path) and os.access(path, os.X_OK)

def get_ytdlp_path():
    """Get the path to the yt-dlp executable."""
    if platform.system() == "Windows":
        return os.path.join(os.getcwd(), "yt-dlp.exe")
    else:
        # For Unix-like systems (Linux, macOS)
        return "yt-dlp"

def get_ffmpeg_path():
    """Get the path to the FFmpeg executable."""
    try:
        import subprocess
        command = ['where' if platform.system() == 'Windows' else 'which', 'ffmpeg']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')[0]  # Take first result on Windows
    except:
        return "ffmpeg"  # Fallback to PATH

def get_ffprobe_path():
    """Get the path to the FFprobe executable."""
    try:
        import subprocess
        command = ['where' if platform.system() == 'Windows' else 'which', 'ffprobe']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')[0]  # Take first result on Windows
    except:
        return "ffprobe"  # Fallback to PATH
