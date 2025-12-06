"""
Path management for external executables.

This module provides utility functions for locating and managing paths to
external executables and directories used by the bot.
"""
import os
import sys
import platform

def _is_executable(path):
    """
    Check if a file exists and is executable.
    
    Args:
        path (str): Path to the file to check
        
    Returns:
        bool: True if the file exists and is executable, False otherwise
    """
    return os.path.isfile(path) and os.access(path, os.X_OK)

def get_ytdlp_path():
    """
    Get the path to the yt-dlp executable.
    
    Returns the path to the yt-dlp executable based on the operating system.
    For Windows, it returns the path to yt-dlp.exe in the root directory.
    For Unix-like systems, it assumes yt-dlp is in the system PATH.
    
    Returns:
        str: Path to the yt-dlp executable
    """
    if platform.system() == "Windows":
        return os.path.join(get_root_dir(), "yt-dlp.exe")
    else:
        # For Unix-like systems (Linux, macOS)
        return "yt-dlp"

def get_ffmpeg_path():
    """
    Get the path to the FFmpeg executable.
    
    Attempts to locate the ffmpeg executable using the system's 'where' or 'which'
    command depending on the platform. Falls back to assuming ffmpeg is in the
    system PATH if the command fails.
    
    Returns:
        str: Path to the FFmpeg executable
    """
    try:
        import subprocess
        import platform
        command = ['where' if platform.system() == 'Windows' else 'which', 'ffmpeg']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')[0]  # Take first result on Windows
    except Exception:
        return "ffmpeg"  # Fallback to PATH

def get_ffprobe_path():
    """
    Get the path to the FFprobe executable.
    
    Attempts to locate the ffprobe executable using the system's 'where' or 'which'
    command depending on the platform. Falls back to assuming ffprobe is in the
    system PATH if the command fails.
    
    Returns:
        str: Path to the FFprobe executable
    """
    try:
        import subprocess
        import platform
        command = ['where' if platform.system() == 'Windows' else 'which', 'ffprobe']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')[0]  # Take first result on Windows
    except Exception:
        return "ffprobe"  # Fallback to PATH

def get_root_dir():
    """
    Get the root directory of the project.
    
    Returns the absolute path to the root directory of the project,
    which is the parent directory of the directory containing this file.
    
    Returns:
        str: Absolute path to the root directory
    """
    return os.path.dirname(os.path.dirname(__file__))

def get_downloads_dir():
    """
    Get the path to the downloads directory.
    
    Returns the absolute path to the downloads directory, which is
    located in the root directory of the project.
    
    Returns:
        str: Absolute path to the downloads directory
    """
    return os.path.join(get_root_dir(), 'downloads')

def get_cache_dir():
    """
    Get the path to the cache directory.
    
    Returns the absolute path to the cache directory, which is
    located in the root directory of the project.
    
    Returns:
        str: Absolute path to the cache directory
    """
    return os.path.join(get_root_dir(), '.cache')

def get_cache_file(filename):
    """
    Get the path to a cache file.
    
    Args:
        filename (str): Name of the cache file
        
    Returns:
        str: Absolute path to the cache file
    """
    return os.path.join(get_cache_dir(), filename)

def get_absolute_path(relative_path):
    """
    Convert a relative path to absolute path from root directory.
    
    Args:
        relative_path (str): Relative path from the root directory
        
    Returns:
        str: Absolute path
    """
    return os.path.join(get_root_dir(), relative_path)

def get_relative_path(absolute_path):
    """
    Convert an absolute path to relative path from root directory.
    
    Args:
        absolute_path (str): Absolute path to convert
        
    Returns:
        str: Path relative to the root directory
    """
    return os.path.relpath(absolute_path, get_root_dir())
