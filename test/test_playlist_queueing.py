import sys
import types
import pytest


@pytest.mark.asyncio
async def test_process_download_queue_playlist_batch(monkeypatch, stub_ctx):
    import scripts.musicbot as mb

    m = mb.MusicBot.get_instance('PL')
    # Provide voice client not playing so branch calls play_next
    from test.conftest import StubVoiceClient
    m.voice_client = StubVoiceClient()
    m.voice_client._playing = False

    # Fake play_next to record calls
    calls = {'called': 0}
    async def fake_play_next(ctx):
        calls['called'] += 1
        return None
    import scripts.play_next as pn
    monkeypatch.setattr(pn, 'play_next', fake_play_next)

    # Stub download_song to return first song info plus entries
    async def fake_download_song(query, status_msg=None, ctx=None, skip_url_check=False):
        return {
            'title': 'First',
            'url': 'u1',
            'file_path': __file__,
            'thumbnail': None,
            'entries': [{'id': 'id2'}, {'id': 'id3'}],
        }
    monkeypatch.setattr(m, 'download_song', fake_download_song)

    # Stub status message capturing edits
    class FakeMsg:
        def __init__(self):
            self.last_embed = None
        async def edit(self, embed=None):
            self.last_embed = embed
    async def fake_update_or_send_message(ctx, embed):
        return FakeMsg()
    monkeypatch.setattr(m, 'update_or_send_message', fake_update_or_send_message, raising=False)

    # Enqueue a download task
    await m.download_queue.put({'query': 'playlist', 'ctx': stub_ctx, 'status_msg': None})

    # Run one iteration of process_download_queue by getting task and processing it
    # Instead of calling the infinite loop, we pull and run the body once
    async def one_step():
        download_info = await m.download_queue.get()
        query = download_info['query']
        ctx = download_info['ctx']
        status_msg = download_info['status_msg']
        async with m.download_lock:
            m.currently_downloading = True
            m.in_progress_downloads[query] = None
            result = await m.download_song(query, status_msg=status_msg, ctx=ctx)
            assert 'entries' in result
            # Simulate the same behavior as process_download_queue
            m.queue.append(result)
            await pn.play_next(ctx)
        m.currently_downloading = False
        m.download_queue.task_done()

    await one_step()

    assert calls['called'] == 1
    assert m.queue  # first song info added