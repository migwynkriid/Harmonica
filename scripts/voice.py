import discord
import time
import asyncio
from scripts.messages import update_or_send_message

async def join_voice_channel(bot_instance, ctx):
    """Join the user's voice channel"""
    if not ctx.author.voice:
        await update_or_send_message(ctx, embed=bot_instance.create_embed("Error", "You must be in a voice channel to use this command!", color=0xe74c3c))
        return False

    try:
        channel = ctx.author.voice.channel
        if bot_instance.voice_client:
            try:
                if bot_instance.voice_client.is_connected():
                    await bot_instance.voice_client.disconnect(force=True)
            except:
                pass
            bot_instance.voice_client = None

        bot_instance.voice_client = await channel.connect(self_deaf=True)
        bot_instance.last_activity = time.time()
        return bot_instance.voice_client.is_connected()

    except Exception as e:
        print(f"Error joining voice channel: {str(e)}")
        await update_or_send_message(ctx, embed=bot_instance.create_embed("Error", "Failed to join voice channel!", color=0xe74c3c))
        bot_instance.voice_client = None
        return False

async def leave_voice_channel(bot_instance):
    """Leave voice channel and cleanup"""
    try:
        if bot_instance.voice_client:
            if bot_instance.voice_client.is_playing():
                bot_instance.voice_client.stop()
            if bot_instance.voice_client.is_connected():
                await bot_instance.voice_client.disconnect(force=True)
    except Exception as e:
        print(f"Error leaving voice channel: {str(e)}")
    finally:
        bot_instance.voice_client = None
        bot_instance.current_song = None