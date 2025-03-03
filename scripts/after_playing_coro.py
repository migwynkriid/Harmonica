import asyncio
import discord
from scripts.play_next import play_next
from scripts.messages import update_or_send_message, create_embed
from scripts.activity import update_activity

class AfterPlayingHandler:
    """
    Handler class for managing what happens after a song finishes playing.
    
    This class provides functionality for handling the transition between songs,
    updating the now playing message, and starting the next song in the queue.
    It is designed to be used as a mixin with the MusicBot class.
    """
    
    async def after_playing_coro(self, error, ctx):
        """
        Coroutine called after a song finishes playing.
        
        This method handles the transition between songs, updates the now playing
        message, and starts the next song in the queue if available.
        
        Args:
            error: Error that occurred during playback, if any
            ctx: Discord command context
        """
        # Handle any playback errors
        if error:
            print(f"Error in playback: {error}")
        
        # Update playback state
        if hasattr(self, 'playback_state'):
            self.playback_state = "stopped"

        # Add a short delay to ensure a clean state after the song ends
        await asyncio.sleep(0.5)

        # Check if there's an after_song_callback (for loop mode)
        if hasattr(self, 'after_song_callback') and self.after_song_callback:
            await self.after_song_callback()
        
        # Check the status of the download queue
        if not self.download_queue.empty():
            print(f"Download queue size: {self.download_queue.qsize()}")
        if not self.currently_downloading and not self.download_queue.empty():
            print("More songs in download queue, continuing processing...")    
        if len(self.queue) == 0 and not self.download_queue.empty():
            print("Waiting for next song to finish downloading...")
            await asyncio.sleep(1)
            
        # Check if the bot has been explicitly stopped
        if hasattr(self, 'explicitly_stopped') and self.explicitly_stopped:
            # If the bot was explicitly stopped, don't play anything
            self.queue.clear()
            return
            
        # Play the next song if available
        if len(self.queue) > 0 or not self.download_queue.empty():
            # Make sure we have a valid context before proceeding
            if ctx and hasattr(ctx, 'guild') and ctx.guild:
                await play_next(ctx)
            else:
                print("Error: Invalid context for play_next in after_playing_coro")
                # Clear the queue to prevent further attempts with invalid context
                self.queue.clear()
        else:
            # Update the now playing message to show that the song has finished
            if self.now_playing_message and self.current_song and isinstance(self.current_song, dict):
                try:
                    # Check if the song is looped
                    loop_cog = None
                    if hasattr(self, 'bot') and self.bot and hasattr(self.bot, 'get_cog'):
                        loop_cog = self.bot.get_cog('Loop')
                    is_looped = loop_cog and self.current_song['url'] in loop_cog.looped_songs if loop_cog else False

                    # For looped songs that weren't skipped, just delete the message
                    if is_looped and not (hasattr(self, 'was_skipped') and self.was_skipped):
                        await self.now_playing_message.delete()
                    else:
                        # For non-looped songs or skipped songs, show an appropriate message
                        title = "Skipped song" if hasattr(self, 'was_skipped') and self.was_skipped else "Finished playing"
                        
                        # Use the context stored in the current_song if the provided ctx is invalid
                        message_ctx = ctx
                        if not (ctx and hasattr(ctx, 'guild') and ctx.guild):
                            message_ctx = self.current_song.get('ctx')
                            
                        finished_embed = create_embed(
                            title,
                            f"[{self.current_song['title']}]({self.current_song['url']})",
                            color=0x808080,
                            thumbnail_url=self.current_song.get('thumbnail'),
                            ctx=message_ctx
                        )
                        # Remove buttons when the song is finished
                        await self.now_playing_message.edit(embed=finished_embed, view=None)
                        
                        # Reset the skipped flag after updating the message
                        if hasattr(self, 'was_skipped'):
                            self.was_skipped = False
                except Exception as e:
                    print(f"Error updating finished message: {str(e)}")
            
            # Update activity status
            if hasattr(self, 'bot') and self.bot:
                await update_activity(self.bot, is_playing=False)
            
            # Reset the playback state
            self.is_playing = False
            self.current_song = None