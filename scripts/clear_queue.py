import asyncio

def clear_queue():
    """Clear both download and playback queues"""
    try:
        from bot import music_bot
        
        music_bot.queue.clear()
        
        items_removed = 0
        while not music_bot.download_queue.empty():
            try:
                music_bot.download_queue.get_nowait()
                items_removed += 1
            except asyncio.QueueEmpty:
                break
        
        for _ in range(items_removed):
            music_bot.download_queue.task_done()
            
    except Exception as e:
        print(f"Error clearing queue: {e}")