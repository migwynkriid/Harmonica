"""
Path management for external executables.
"""
import os
import sys
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
    # Use ffmpeg from PATH for all platforms
    return "ffmpeg"
