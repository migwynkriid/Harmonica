"""
JavaScript runtime detection and configuration for yt-dlp.

This module provides utility functions for detecting and configuring
JavaScript runtimes (Node.js, Deno, Bun, QuickJS) that yt-dlp needs
to solve YouTube's JavaScript challenges.
"""
import os
import sys
import subprocess
import shutil
from scripts.constants import GREEN, BLUE, RESET, YELLOW, RED

def install_nodejs_windows():
    """
    Install Node.js on Windows using winget.
    
    Attempts to install Node.js LTS using the Windows Package Manager (winget).
    
    Returns:
        bool: True if installation was successful, False otherwise
    """
    try:
        print(f"{YELLOW}Node.js not found. Installing Node.js LTS using winget...{RESET}")
        subprocess.run(['winget', 'install', 'OpenJS.NodeJS.LTS', '--silent'], check=True)
        print(f"{GREEN}Node.js installed successfully. Please restart the bot for changes to take effect.{RESET}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error installing Node.js: {e}{RESET}")
        print(f"{YELLOW}Please install Node.js manually from https://nodejs.org/{RESET}")
        return False

def install_nodejs_macos():
    """
    Install Node.js on macOS using Homebrew.
    
    Attempts to install Node.js using Homebrew.
    
    Returns:
        bool: True if installation was successful, False otherwise
    """
    try:
        print(f"{YELLOW}Node.js not found. Attempting to install Node.js using Homebrew...{RESET}")
        subprocess.run(['brew', 'install', 'node'], check=True)
        print(f"{GREEN}Node.js installed successfully. Please restart the bot for changes to take effect.{RESET}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error installing Node.js: {e}{RESET}")
        print(f"{YELLOW}Please install Node.js manually from https://nodejs.org/{RESET}")
        return False

def install_nodejs_linux():
    """
    Install Node.js on Linux using NodeSource setup script.
    
    Attempts to install Node.js v20.x LTS using NodeSource repository for Debian/Ubuntu.
    This ensures a modern version is installed rather than older versions from default repos.
    
    Returns:
        bool: True if installation was successful, False otherwise
    """
    try:
        print(f"{YELLOW}Node.js not found. Installing Node.js v20.x LTS using NodeSource...{RESET}")
        # Download and run NodeSource setup script for Node.js 20.x
        setup_script = subprocess.run(
            ['curl', '-fsSL', 'https://deb.nodesource.com/setup_20.x'],
            capture_output=True,
            check=True,
            text=True
        )
        subprocess.run(['sudo', 'bash', '-c', setup_script.stdout], check=True)
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'nodejs'], check=True)
        print(f"{GREEN}Node.js installed successfully. Please restart the bot for changes to take effect.{RESET}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error installing Node.js: {e}{RESET}")
        print(f"{YELLOW}Please install Node.js manually from https://nodejs.org/ or use nvm{RESET}")
        return False

def check_runtime(command):
    """
    Check if a JavaScript runtime is available.
    
    Args:
        command (str): The command name to check (e.g., 'node', 'deno', 'bun', 'qjs')
        
    Returns:
        tuple: (runtime_path, version_string) or (None, None) if not found
    """
    try:
        # Use shutil.which to find the executable in PATH (cross-platform)
        runtime_path = shutil.which(command)
        if runtime_path:
            # Verify it actually runs and get version
            result = subprocess.run([runtime_path, '--version'], capture_output=True, check=True, timeout=5, text=True)
            version_string = result.stdout.strip()
            return (runtime_path, version_string)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return (None, None)

def get_available_js_runtime():
    """
    Detect available JavaScript runtimes in priority order.
    
    Checks for available JavaScript runtimes in this order:
    1. Node.js (most common, good compatibility) - requires v20.0.0+
    2. Deno (recommended by yt-dlp) - requires v2.0.0+
    3. Bun (fast) - requires v1.0.31+
    4. QuickJS (fallback, slower) - requires 2023-12-9+
    
    Returns:
        tuple: (runtime_name, runtime_path, version_string, is_supported) or (None, None, None, False) if none found
    """
    # Check in priority order with minimum versions
    runtime_checks = [
        ('node', 'node', 20, 0, 0),      # Minimum: v20.0.0
        ('deno', 'deno', 2, 0, 0),       # Minimum: v2.0.0
        ('bun', 'bun', 1, 0, 31),        # Minimum: v1.0.31
        ('quickjs', 'qjs', 2023, 12, 9), # Minimum: 2023-12-9
    ]
    
    for runtime_name, command, min_major, min_minor, min_patch in runtime_checks:
        runtime_path, version_string = check_runtime(command)
        if runtime_path and version_string:
            # Parse version for Node.js to check if it's supported
            if runtime_name == 'node':
                try:
                    # Node version format: v20.0.0
                    version_clean = version_string.lstrip('v')
                    parts = version_clean.split('.')
                    major = int(parts[0])
                    if major < min_major:
                        return (runtime_name, runtime_path, version_string, False)  # Unsupported version
                except (ValueError, IndexError):
                    pass  # Can't parse version, assume it's ok
            
            return (runtime_name, runtime_path, version_string, True)
    
    return (None, None, None, False)

def get_js_runtime_config(verbose=False):
    """
    Get yt-dlp configuration for JavaScript runtime.
    
    Detects available JavaScript runtimes and returns the appropriate
    configuration for yt-dlp to use. If no runtime is found, attempts to
    install Node.js automatically.
    
    Args:
        verbose (bool): If True, print detection results
    
    Returns:
        dict: Dict in format {runtime_name: {'path': runtime_path}} or empty dict if none found
    """
    runtime_name, runtime_path, version_string, is_supported = get_available_js_runtime()
    
    if runtime_name and runtime_path:
        if verbose:
            if is_supported:
                print(f"{GREEN}JavaScript runtime detected: {runtime_name} at {BLUE}{runtime_path}{RESET}")
            else:
                print(f"{YELLOW}JavaScript runtime detected: {runtime_name} {version_string} at {BLUE}{runtime_path}{RESET}")
                print(f"{RED}⚠ WARNING: This version is UNSUPPORTED. Node.js v20.0.0+ is required.{RESET}")
                print(f"{YELLOW}  YouTube downloads will fail. Attempting to install Node.js v20+...{RESET}")
                # Try to install a newer version
                install_result = ensure_nodejs_installed()
                if install_result:
                    print(f"{GREEN}Node.js installation initiated. Please restart the bot.{RESET}")
        return {runtime_name: {'path': runtime_path}}
    else:
        if verbose:
            print(f"{YELLOW}⚠ No JavaScript runtime found.{RESET}")
            print(f"{YELLOW}  Attempting to install Node.js v20+ LTS...{RESET}")
        # Try to install Node.js
        install_result = ensure_nodejs_installed()
        if install_result:
            if verbose:
                print(f"{GREEN}Node.js installation initiated. Please restart the bot.{RESET}")
        else:
            if verbose:
                print(f"{YELLOW}  Install Node.js v20+ from https://nodejs.org/ or Deno v2+ from https://deno.com/{RESET}")
        return {}

def ensure_nodejs_installed():
    """
    Ensure Node.js is installed on the system.
    
    Checks if Node.js is available and attempts to install it if not found.
    Uses platform-specific package managers (winget, brew, apt).
    
    Returns:
        bool: True if installation was successful or initiated, False otherwise
    """
    # Check if Node.js is already available
    node_path, version = check_runtime('node')
    if node_path:
        return True
    
    # Attempt to install based on OS
    if sys.platform.startswith('win'):
        return install_nodejs_windows()
    elif sys.platform.startswith('darwin'):
        return install_nodejs_macos()
    else:
        return install_nodejs_linux()

def check_ejs_package():
    """
    Check if yt-dlp-ejs package is installed.
    
    Returns:
        bool: True if yt-dlp-ejs is installed, False otherwise
    """
    try:
        import importlib.util
        spec = importlib.util.find_spec('yt_dlp_ejs')
        return spec is not None
    except (ImportError, ValueError):
        return False

def ensure_ejs_installed(verbose=False):
    """
    Ensure EJS challenge solver scripts are available.
    
    Checks if the yt-dlp-ejs package is installed. If not, prints a warning
    and suggests installation methods.
    
    Args:
        verbose (bool): If True, print installation status
    
    Returns:
        bool: True if EJS is available, False otherwise
    """
    if check_ejs_package():
        if verbose:
            print("✓ yt-dlp-ejs package is installed")
        return True
    else:
        if verbose:
            print("⚠ yt-dlp-ejs package not found. YouTube challenge solving may fail.")
            print("  To fix this, run: pip install -U 'yt-dlp'")
        print("  Alternatively, the bot will attempt to download scripts from GitHub automatically.")
        return False
