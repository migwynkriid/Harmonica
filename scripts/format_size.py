def format_size(bytes):
    """
    Format bytes into human readable size.
    
    Converts a byte count into a human-readable string with appropriate
    units (B, KB, MB, GB, TB). The function automatically selects the
    best unit to make the number readable.
    
    Args:
        bytes: The size in bytes to format
        
    Returns:
        str: A formatted string representing the size with appropriate units
             (e.g., "15.50 MB" or "1.20 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"