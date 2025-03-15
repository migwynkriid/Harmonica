import asyncio
import time
from scripts.clear_queue import clear_queue
from scripts.constants import GREEN, BLUE, RESET

async def start_inactivity_checker(bot_instance):
    """
    Start the inactivity checker.
    
    This function initializes the inactivity checker task that monitors
    voice channel activity and disconnects the bot after a period of inactivity.
    
    Args:
        bot_instance: The MusicBot instance to monitor for inactivity
    """
    try:
        await check_inactivity(bot_instance)
        bot_instance._inactivity_task = bot_instance.bot_loop.create_task(check_inactivity(bot_instance))
    except Exception as e:
        print(f"Error starting inactivity checker: {str(e)}")

async def check_inactivity(bot_instance):
    """
    Check for inactivity and leave voice if inactive too long.
    
    This function runs in a continuous loop, checking if the bot has been
    inactive in a voice channel for longer than the configured timeout period.
    If the bot is inactive and not playing music, it will disconnect from
    the voice channel and clear the queue.
    
    Args:
        bot_instance: The MusicBot instance to monitor for inactivity
    """
    while True:
        try:
            await asyncio.sleep(60)
            
            # Get all server instances
            for guild_id, server_bot in bot_instance.__class__._instances.items():
                # Skip the setup instance
                if guild_id == 'setup':
                    continue
                    
                if server_bot.voice_client and server_bot.voice_client.is_connected():
                    # Check if there are active downloads
                    has_active_downloads = (
                        server_bot.currently_downloading or 
                        server_bot.in_progress_downloads or
                        server_bot.current_download_task is not None or
                        server_bot.current_ydl is not None
                    )
                    
                    # Reset activity timer if music is playing, there are songs in queue, or there are active downloads
                    if (server_bot.voice_client.is_playing() or 
                        server_bot.queue or 
                        has_active_downloads or
                        server_bot.waiting_for_song):
                        server_bot.last_activity = time.time()
                    # Only disconnect if inactive AND no music is playing/queued AND no active downloads
                    elif (time.time() - server_bot.last_activity > server_bot.inactivity_timeout and 
                          server_bot.inactivity_leave and 
                          not server_bot.voice_client.is_playing() and 
                          not server_bot.queue and
                          not has_active_downloads and
                          not server_bot.waiting_for_song):
                        # Get the server name from the voice client's guild
                        server_name = server_bot.voice_client.guild.name if server_bot.voice_client.guild else "Unknown Server"
                        print(f"{GREEN}Left voice chat in {RESET}{BLUE}{server_name}{RESET}{GREEN} due to inactivity{RESET}")
                        # Cancel any active downloads before disconnecting
                        await server_bot.cancel_downloads()
                        await server_bot.voice_client.disconnect()
                        # Clear queue for this specific server
                        clear_queue(guild_id)
                        
        except Exception as e:
            print(f"Error in inactivity checker: {str(e)}")
            await asyncio.sleep(60)
