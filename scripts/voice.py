import discord
import time
import asyncio
import json
import logging
from scripts.messages import update_or_send_message, create_embed
from scripts.constants import GREEN, BLUE, RESET
import sys
import warnings

def get_voice_config():
    """
    Get voice configuration from config.json
    
    Reads the voice-related settings from the config file, which control
    behaviors like auto-leaving empty channels and inactivity timeouts.
    
    Returns:
        dict: Voice configuration settings or default values if file can't be read
    """
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            return config.get('VOICE', {})
    except Exception as e:
        logging.error(f"Error reading config.json: {str(e)}")
        return {"AUTO_LEAVE_EMPTY": True}  # Default values

# Set up task exception handling
def _handle_task_exception(loop, context):
    """Custom exception handler for asyncio tasks."""
    exception = context.get('exception')
    if exception is None:
        msg = context.get('message')
        if 'Task was destroyed but it is pending' in msg:
            # Just log with info level rather than as an error
            logging.info(f"Task destruction: {msg}")
            return
        
    # For other exceptions, use the default handler
    loop.default_exception_handler(context)

async def join_voice_channel(bot_instance, ctx):
    """
    Join the user's voice channel
    
    Connects the bot to the voice channel where the command author is currently in.
    Handles various checks and error cases such as the user not being in a voice channel
    or the channel being empty when AUTO_LEAVE_EMPTY is enabled.
    
    Args:
        bot_instance: The bot instance containing voice client and state
        ctx: The command context containing information about the invoker
        
    Returns:
        bool: True if successfully joined, False otherwise
    """
    # Set up safe task exception handling
    loop = asyncio.get_event_loop()
    if sys.version_info >= (3, 8):
        loop.set_exception_handler(_handle_task_exception)
    
    # Check if user is in a voice channel
    if not ctx.author.voice:
        await update_or_send_message(ctx, embed=create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c))
        return False

    try:
        channel = ctx.author.voice.channel
        voice_config = get_voice_config()
        
        # Check if the channel is empty (except for the bot) when AUTO_LEAVE_EMPTY is enabled
        if voice_config.get('AUTO_LEAVE_EMPTY', True):
            members_in_channel = len([m for m in channel.members if not m.bot])
            if members_in_channel == 0:
                await update_or_send_message(ctx, embed=create_embed("Error", "Cannot join an empty voice channel!", color=0xe74c3c))
                return False

        # Clean up existing voice connection
        if bot_instance.voice_client:
            try:
                if bot_instance.voice_client.is_connected():
                    # Use proper disconnect method with a timeout
                    disconnect_task = asyncio.create_task(bot_instance.voice_client.disconnect(force=True))
                    try:
                        await asyncio.wait_for(disconnect_task, timeout=5.0)
                    except asyncio.TimeoutError:
                        logging.warning("Voice disconnect timed out, proceeding anyway")
                    except Exception as e:
                        logging.warning(f"Error during voice disconnect: {e}")
            except Exception as e:
                logging.warning(f"Error cleaning up voice client: {e}")
            
            # Ensure voice client is reset
            bot_instance.voice_client = None
            # Small delay to ensure disconnection is processed
            await asyncio.sleep(0.5)

        # Connect to the voice channel with self_deaf=True to avoid listening to audio
        connect_task = asyncio.create_task(channel.connect(self_deaf=True))
        try:
            bot_instance.voice_client = await asyncio.wait_for(connect_task, timeout=10.0)
            bot_instance.last_activity = time.time()
            return bot_instance.voice_client.is_connected()
        except asyncio.TimeoutError:
            logging.error("Voice connection timed out")
            return False
        except Exception as e:
            logging.error(f"Voice connection failed: {e}")
            return False

    except Exception as e:
        logging.error(f"Error joining voice channel: {str(e)}")
        await update_or_send_message(ctx, embed=create_embed("Error", "Failed to join voice channel!", color=0xe74c3c))
        bot_instance.voice_client = None
        return False

async def leave_voice_channel(bot_instance):
    """
    Leave voice channel and cleanup resources
    
    Disconnects the bot from the voice channel, stops any playing audio,
    and resets related state variables.
    
    Args:
        bot_instance: The bot instance containing voice client and state
    """
    # Set up safe task exception handling
    loop = asyncio.get_event_loop()
    if sys.version_info >= (3, 8):
        loop.set_exception_handler(_handle_task_exception)
        
    try:
        if bot_instance.voice_client:
            if bot_instance.voice_client.is_playing():
                bot_instance.voice_client.stop()
            if bot_instance.voice_client.is_connected():
                # Use a task with timeout for safer disconnection
                disconnect_task = asyncio.create_task(bot_instance.voice_client.disconnect(force=True))
                try:
                    await asyncio.wait_for(disconnect_task, timeout=5.0)
                except asyncio.TimeoutError:
                    logging.warning("Voice disconnect timed out during leave_voice_channel")
                except Exception as e:
                    logging.warning(f"Error during voice disconnect in leave_voice_channel: {e}")
    except Exception as e:
        logging.error(f"Error leaving voice channel: {str(e)}")
    finally:
        # Reset bot state variables
        bot_instance.voice_client = None
        bot_instance.current_song = None

async def handle_voice_state_update(bot_instance, member, before, after):
    """
    Handle voice state updates for the bot
    
    This event handler is triggered whenever a voice state changes in the server.
    It's primarily used to detect when the bot is alone in a voice channel and
    should disconnect according to the AUTO_LEAVE_EMPTY configuration.
    
    Args:
        bot_instance: The bot instance containing voice client and state
        member: The member whose voice state changed
        before: The voice state before the change
        after: The voice state after the change
    """
    # Check if bot_instance is None or a class instead of an instance
    if not bot_instance or isinstance(bot_instance, type) or not hasattr(bot_instance, 'voice_client') or not bot_instance.voice_client:
        return

    bot_voice_channel = bot_instance.voice_client.channel
    if not bot_voice_channel:
        return

    # Get guild ID for server-specific operations
    guild_id = None
    if hasattr(bot_instance, 'guild_id'):
        guild_id = bot_instance.guild_id

    # Only check for empty channel if AUTO_LEAVE_EMPTY is enabled
    voice_config = get_voice_config()
    if voice_config.get('AUTO_LEAVE_EMPTY', True):
        # Count non-bot members in the channel
        members_in_channel = sum(1 for m in bot_voice_channel.members if not m.bot)

        if members_in_channel == 0:
            if bot_instance and bot_instance.voice_client and bot_instance.voice_client.is_connected():
                server_name = bot_voice_channel.guild.name if bot_voice_channel and hasattr(bot_voice_channel, 'guild') else "Unknown Server"
                print(f"{GREEN}Leaving empty voice channel: {RESET}{BLUE}{bot_voice_channel.name}{RESET}{GREEN} in server: {RESET}{BLUE}{server_name}{RESET}")

                # First, disconnect from voice channel immediately
                await bot_instance.voice_client.disconnect()
                # Then stop playback and clear the queue
                if bot_instance.voice_client.is_playing() or bot_instance.queue:
                    bot_instance.voice_client.stop()
                    bot_instance.queue.clear()

                # Cancel any active downloads
                await bot_instance.cancel_downloads()

                # Clear the queue for this specific server
                from scripts.clear_queue import clear_queue
                if hasattr(bot_instance, 'guild_id'):
                    clear_queue(bot_instance.guild_id)
                else:
                    clear_queue()

                # Create a list of messages to delete to avoid dictionary size change during iteration
                queued_messages = list(bot_instance.queued_messages.values())
                for msg in queued_messages:
                    try:
                        await msg.delete()
                        await asyncio.sleep(0.5)  # Add 0.5-second delay between deletions to avoid rate limits
                    except:
                        pass
                bot_instance.queued_messages.clear()
                
                # Update the now playing message to show it was stopped
                if bot_instance.now_playing_message and bot_instance.current_song:
                    try:
                        description = f"[{bot_instance.current_song['title']}]({bot_instance.current_song['url']})"
                        
                        stopped_embed = create_embed(
                            "Finished playing",
                            description,
                            color=0x808080,
                            thumbnail_url=bot_instance.current_song.get('thumbnail'),
                            ctx=bot_instance.current_song.get('ctx')  # Pass the original context to maintain requester info
                        )
                        await bot_instance.now_playing_message.edit(embed=stopped_embed, view=None)
                    except Exception as e:
                        print(f"Error updating now playing message: {str(e)}")
                
                # Set explicitly_stopped flag to prevent further playback
                bot_instance.explicitly_stopped = True
                
                # Reset bot state variables
                bot_instance.current_song = None
                bot_instance.is_playing = False
                bot_instance.now_playing_message = None
                await bot_instance.update_activity()