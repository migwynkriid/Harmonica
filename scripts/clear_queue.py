import asyncio

def clear_queue(guild_id=None):
    """Clear both download and playback queues
    
    Args:
        guild_id: Optional guild ID to clear queue for a specific server
                  If None, clears all queues for all servers
    """
    try:
        from bot import MusicBot
        
        if guild_id:
            # Clear queue for a specific server
            server_music_bot = MusicBot.get_instance(str(guild_id))
            
            server_music_bot.queue.clear()
            
            items_removed = 0
            while not server_music_bot.download_queue.empty():
                try:
                    server_music_bot.download_queue.get_nowait()
                    items_removed += 1
                except asyncio.QueueEmpty:
                    break
            
            for _ in range(items_removed):
                server_music_bot.download_queue.task_done()
        else:
            # Clear queues for all servers
            for guild_id, server_music_bot in MusicBot._instances.items():
                server_music_bot.queue.clear()
                
                items_removed = 0
                while not server_music_bot.download_queue.empty():
                    try:
                        server_music_bot.download_queue.get_nowait()
                        items_removed += 1
                    except asyncio.QueueEmpty:
                        break
                
                for _ in range(items_removed):
                    server_music_bot.download_queue.task_done()
            
    except Exception as e:
        print(f"Error clearing queue: {e}")