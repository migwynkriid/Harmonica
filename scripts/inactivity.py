import asyncio
import time
from scripts.clear_queue import clear_queue

async def start_inactivity_checker(bot_instance):
    """Start the inactivity checker"""
    try:
        await check_inactivity(bot_instance)
        bot_instance._inactivity_task = bot_instance.bot_loop.create_task(check_inactivity(bot_instance))
    except Exception as e:
        print(f"Error starting inactivity checker: {str(e)}")

async def check_inactivity(bot_instance):
    """Check for inactivity and leave voice if inactive too long"""
    while True:
        try:
            await asyncio.sleep(60)
            
            if bot_instance.voice_client and bot_instance.voice_client.is_connected():
                if bot_instance.voice_client.is_playing():
                    bot_instance.last_activity = time.time()
                elif time.time() - bot_instance.last_activity > bot_instance.inactivity_timeout and bot_instance.inactivity_leave:
                    print(f"Leaving voice channel due to {bot_instance.inactivity_timeout} seconds of inactivity")
                    await bot_instance.voice_client.disconnect()
                    clear_queue()
        except Exception as e:
            print(f"Error in inactivity checker: {str(e)}")
            await asyncio.sleep(60)
