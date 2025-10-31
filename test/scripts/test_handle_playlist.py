import pytest


@pytest.mark.asyncio
async def test_process_playlist_downloads(monkeypatch, stub_ctx):
    import scripts.handle_playlist as hp
    calls = {'played': 0}
    async def fake_play_next(ctx):
        calls['played'] += 1
    import scripts.play_next as pn
    monkeypatch.setattr(pn, 'play_next', fake_play_next)

    class MB(hp.PlaylistHandler):
        def __init__(self):
            import asyncio
            self.voice_client = type('VC', (), {'is_connected': lambda self: True, 'is_playing': lambda self: False})()
            self.queue_lock = asyncio.Lock()
            self.queue = []
            self.is_playing = False
        async def download_song(self, url, status_msg=None, ctx=None, skip_url_check=False):
            return {'title': 't', 'url': url, 'file_path': __file__, 'thumbnail': None}
    async def fake_duration(fp):
        return 1.23
    monkeypatch.setattr(hp, 'get_audio_duration', fake_duration)
    entries = [{'id': 'abc'}]
    mb = MB()
    await mb._process_playlist_downloads(entries, stub_ctx, status_msg=None)
    assert mb.queue and mb.queue[0]['is_from_playlist'] is True