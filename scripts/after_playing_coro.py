import asyncio
import discord

class AfterPlayingHandler:
    async def after_playing_coro(self, error, ctx):
        """Coroutine called after a song finishes"""
        if error:
            print(f"Error in playback: {error}")
        
        print("Song finished playing, checking queue...")
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
            await self.play_next(ctx)
        else:
            print("All songs finished, updating activity...")
            if self.now_playing_message:
                try:
                    finished_embed = self.create_embed(
                        "Finished Playing",
                        f"[{self.current_song['title']}]({self.current_song['url']})",
                        color=0x808080,
                        thumbnail_url=self.current_song.get('thumbnail'),
                        ctx=ctx
                    )
                    await self.now_playing_message.edit(embed=finished_embed)
                except Exception as e:
                    print(f"Error updating finished message: {str(e)}")
            
            self.is_playing = False
            self.current_song = None
            await self.update_activity()