"""
JavaScript runtime detection and configuration for yt-dlp.

This module provides utility functions for detecting and configuring
JavaScript runtimes (Node.js, Deno, Bun, QuickJS) that yt-dlp needs
to solve YouTube's JavaScript challenges.
"""
import sys
import subprocess
import shutil
from scripts.constants import GREEN, BLUE, RESET, YELLOW, RED

def check_runtime(command):
    """
    Check if a JavaScript runtime is available.
    
    Args:
        command (str): The command name to check (e.g., 'node', 'deno', 'bun', 'qjs')
        
    Returns:
        str or None: Full path to the runtime if found, None otherwise
    """
    try:
        # Use shutil.which to find the executable in PATH (cross-platform)
        runtime_path = shutil.which(command)
        if runtime_path:
            # Verify it actually runs
            subprocess.run([runtime_path, '--version'], capture_output=True, check=True, timeout=5)
            return runtime_path
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None

def get_available_js_runtime():
    """
    Detect available JavaScript runtimes in priority order.
    
    Checks for available JavaScript runtimes in this order:
    1. Node.js (most common, good compatibility)
    2. Deno (recommended by yt-dlp, has restrictions)
    3. Bun (fast, but no permission restrictions)
    4. QuickJS (fallback, slower)
    
    Returns:
        tuple: (runtime_name, runtime_path) or (None, None) if none found
    """
    # Check in priority order
    runtime_checks = [
        ('node', 'node'),
        ('deno', 'deno'),
        ('bun', 'bun'),
        ('quickjs', 'qjs'),  # QuickJS executable is usually named 'qjs'
    ]
    
    for runtime_name, command in runtime_checks:
        runtime_path = check_runtime(command)
        if runtime_path:
            return (runtime_name, runtime_path)
    
    return (None, None)

def get_js_runtime_config(verbose=False):
    """
    Get yt-dlp configuration for JavaScript runtime.
    
    Detects available JavaScript runtimes and returns the appropriate
    configuration for yt-dlp to use.
    
    Args:
        verbose (bool): If True, print detection results
    
    Returns:
        dict: Dict in format {runtime_name: {'path': runtime_path}} or empty dict if none found
    """
    runtime_name, runtime_path = get_available_js_runtime()
    
    if runtime_name and runtime_path:
        if verbose:
            print(f"{GREEN}JavaScript runtime detected: {runtime_name} at {BLUE}{runtime_path}{RESET}")
        return {runtime_name: {'path': runtime_path}}
    else:
        if verbose:
            print(f"{YELLOW}⚠ No JavaScript runtime found. YouTube downloads may fail.{RESET}")
            print(f"{YELLOW}  Install Node.js from https://nodejs.org/ or Deno from https://deno.com/{RESET}")
        return {}

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
