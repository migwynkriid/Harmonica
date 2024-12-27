"""
Path management for external executables.
"""
import os
import sys
import platform

def get_ytdlp_path():
    """Get the path to the yt-dlp executable."""
    if platform.system() == "Windows":
        return os.path.join(os.getcwd(), "yt-dlp.exe")
    else:
        # For Unix-like systems (Linux, macOS)
        return "yt-dlp"

def get_ffmpeg_path():
    """Get the path to the FFmpeg executable."""
    if platform.system() == "Windows":
        return os.path.join(os.getcwd(), "ffmpeg.exe")
    else:
        # For Unix-like systems (Linux, macOS)
        return "ffmpeg"
