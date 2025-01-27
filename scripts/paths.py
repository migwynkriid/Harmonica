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
    if platform.system() == "Windows":
        return os.path.join(os.getcwd(), "ffmpeg.exe")
    elif platform.system() == "Darwin":  # macOS
        # Check common FFmpeg locations on macOS
        macos_paths = [
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/local/bin/ffmpeg"
        ]
        for path in macos_paths:
            if _is_executable(path):
                return path
        # If FFmpeg not found, return default path (will trigger installation)
        return "ffmpeg"
    else:
        # For other Unix-like systems
        return "ffmpeg"
