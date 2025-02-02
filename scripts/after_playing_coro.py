import asyncio
import discord
from scripts.play_next import play_next
from scripts.messages import update_or_send_message, create_embed

class AfterPlayingHandler:
    async def after_playing_coro(self, error, ctx):
        """Coroutine called after a song finishes"""
        if error:
            print(f"Error in playback: {error}")
        
        print("Song ended, checking queue...")
        # Update playback state
        if hasattr(self, 'playback_state'):
            self.playback_state = "stopped"

        # Add delay after song ends to ensure clean state
        await asyncio.sleep(0.5)

        # Check if there's an after_song_callback (for loop mode)
        if hasattr(self, 'after_song_callback') and self.after_song_callback:
            await self.after_song_callback()
        
        if len(self.queue) > 0:
            print(f"Queue length: {len(self.queue)}")
        if not self.download_queue.empty():
            print(f"Download queue size: {self.download_queue.qsize()}")
        if not self.currently_downloading and not self.download_queue.empty():
            print("More songs in download queue, continuing processing...")    
        if len(self.queue) == 0 and not self.download_queue.empty():
            print("Waiting for next song to finish downloading...")
            await asyncio.sleep(1)
        if len(self.queue) > 0 or not self.download_queue.empty():
            await play_next(ctx)
        else:
            print("All songs finished, updating activity...")
            if self.now_playing_message and self.current_song and isinstance(self.current_song, dict):
                try:
                    # Check if the song is looped
                    loop_cog = self.bot.get_cog('Loop')
                    is_looped = loop_cog and self.current_song['url'] in loop_cog.looped_songs

                    # For looped songs that weren't skipped, just delete the message
                    if is_looped and not (hasattr(self, 'was_skipped') and self.was_skipped):
                        await self.now_playing_message.delete()
                    else:
                        # For non-looped songs or skipped songs, show appropriate message
                        title = "Skipped song" if hasattr(self, 'was_skipped') and self.was_skipped else "Finished playing"
                        
                        finished_embed = create_embed(
                            title,
                            f"[{self.current_song['title']}]({self.current_song['url']})",
                            color=0x808080,
                            thumbnail_url=self.current_song.get('thumbnail'),
                            ctx=ctx
                        )
                        # Remove buttons when song is finished
                        await self.now_playing_message.edit(embed=finished_embed, view=None)
                except Exception as e:
                    print(f"Error updating finished message: {str(e)}")
            
            self.is_playing = False
            self.current_song = None
            if hasattr(self, 'was_skipped'):
                self.was_skipped = False  # Reset the skipped flag
            await self.update_activity()