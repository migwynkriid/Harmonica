import asyncio

def clear_download_queue(music_bot):
    """
    Clear download queue and properly mark tasks as done.
    
    This is a shared utility function to avoid duplicating queue clearing logic
    across multiple files.
    
    Args:
        music_bot: The MusicBot instance
        
    Returns:
        int: Number of items removed from download queue
    """
    items_removed = 0
    while not music_bot.download_queue.empty():
        try:
            music_bot.download_queue.get_nowait()
            items_removed += 1
        except asyncio.QueueEmpty:
            break
    
    for _ in range(items_removed):
        music_bot.download_queue.task_done()
    
    return items_removed

def clear_queue(guild_id=None):
    """
    Clear both download and playback queues.
    
    This function clears the song queue and download queue for either a specific
    server or all servers. It ensures that any tasks in the download queue are
    properly marked as done to prevent hanging tasks.
    
    Args:
        guild_id: Optional guild ID to clear queue for a specific server.
                  If None, clears all queues for all servers.
    """
    try:
        from bot import MusicBot
        
        if guild_id:
            # Clear queue for a specific server
            server_music_bot = MusicBot.get_instance(str(guild_id))
            server_music_bot.queue.clear()
            clear_download_queue(server_music_bot)
        else:
            # Clear queues for all servers
            for guild_id, server_music_bot in MusicBot._instances.items():
                server_music_bot.queue.clear()
                clear_download_queue(server_music_bot)
            
    except Exception as e:
        print(f"Error clearing queue: {e}")