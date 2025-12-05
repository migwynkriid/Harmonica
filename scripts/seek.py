import discord
import time
from scripts.config import FFMPEG_OPTIONS
from scripts.messages import create_embed


async def seek_audio(ctx, music_bot, seconds, direction="forward"):
    """
    Seek the currently playing audio forward or backward by a specified number of seconds.
    
    This function handles seeking in the currently playing audio file by:
    1. Calculating the new position based on current playback time
    2. Creating a new FFmpeg audio source with the seek position
    3. Replacing the current audio source without stopping playback
    
    Args:
        ctx: The command context
        music_bot: The music bot instance
        seconds (int): Number of seconds to seek
        direction (str): Either "forward" or "rewind" to indicate seek direction
        
    Returns:
        tuple: (success: bool, message: str, new_position: int or None)
    """
    # Validate that there's a song playing
    if not music_bot.current_song:
        return False, "No song is currently playing!", None
        
    # Check if the bot is connected and playing
    if not music_bot.voice_client or not ctx.voice_client:
        return False, "Not connected to a voice channel", None
        
    # Get current song info
    current_song = music_bot.current_song
    
    # Don't allow seeking on streams
    if current_song.get('is_stream'):
        return False, "Cannot seek on live streams!", None
    
    # Calculate current position in the song
    if music_bot.playback_start_time:
        current_position = int(time.time() - music_bot.playback_start_time)
    else:
        current_position = 0
    
    # Calculate new position based on direction
    if direction == "forward":
        new_position = current_position + seconds
    else:  # rewind
        new_position = current_position - seconds
    
    # Ensure new position is not negative
    if new_position < 0:
        new_position = 0
    
    # Get song duration if available
    duration = current_song.get('duration')
    duration_seconds = None
    if duration:
        try:
            # Convert duration string to seconds if needed
            if isinstance(duration, str):
                # Parse duration format like "3:45" or "1:23:45"
                parts = duration.split(':')
                if len(parts) == 2:  # MM:SS
                    duration_seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:  # HH:MM:SS
                    duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                duration_seconds = int(duration)
        except (ValueError, TypeError):
            # If duration parsing fails, we'll skip duration check
            duration_seconds = None
            
        # Check if new position exceeds duration
        if duration_seconds and new_position >= duration_seconds:
            return False, f"Cannot seek beyond song duration ({duration})", None
    
    try:
        # Create a new FFmpeg audio source with seek position
        ffmpeg_options = FFMPEG_OPTIONS.copy()
        ffmpeg_options['options'] = ffmpeg_options.get('options', '') + f' -ss {new_position}'
        
        # Create new source with seek
        source = discord.FFmpegPCMAudio(current_song['file_path'], **ffmpeg_options)
        
        # Call read() on the audio source before playing to prevent speed-up issue
        source.read()
        
        # Replace the audio source without stopping playback
        ctx.voice_client._player.source = source
        
        # Update playback start time to reflect the new position
        music_bot.playback_start_time = time.time() - new_position
        
        # Update last activity
        music_bot.last_activity = time.time()
        
        # Format the time for display
        def format_time(seconds):
            """Format seconds into MM:SS or HH:MM:SS"""
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            if hours > 0:
                return f"{hours}:{minutes:02d}:{secs:02d}"
            return f"{minutes}:{secs:02d}"
        
        position_str = format_time(new_position)
        return True, position_str, new_position
        
    except Exception as e:
        return False, f"An error occurred while seeking: {str(e)}", None
