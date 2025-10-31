import pytest


@pytest.mark.asyncio
async def test_process_playlist_downloads_batch(monkeypatch, stub_ctx):
    import scripts.handle_playlist as hp

    class VC:
        def __init__(self):
            self._connected = True
        def is_connected(self):
            return self._connected
        def is_playing(self):
            return False

    calls = {"played": 0}
    async def fake_play_next(ctx):
        calls["played"] += 1
    import scripts.play_next as pn
    import scripts.handle_playlist as hp_mod
    # Patch both modules' play_next references
    monkeypatch.setattr(pn, 'play_next', fake_play_next)
    monkeypatch.setattr(hp_mod, 'play_next', fake_play_next)

    async def fake_duration(fp):
        return 1.0
    monkeypatch.setattr(hp, 'get_audio_duration', fake_duration)

    class MB(hp.PlaylistHandler):
        def __init__(self):
            import asyncio
            self.voice_client = VC()
            self.queue_lock = asyncio.Lock()
            self.queue = []
            self.is_playing = False
            self.bot = None
        async def download_song(self, url, status_msg=None, skip_url_check=True):
            return {'title': 't', 'url': url, 'file_path': __file__, 'thumbnail': None}

    mb = MB()
    entries = [{'id': 'A'}, {'id': 'B'}, {'id': 'C'}]
    await mb._process_playlist_downloads(entries, stub_ctx, status_msg=None)

    assert len(mb.queue) == 3
    assert all(s.get('is_from_playlist') for s in mb.queue)
    assert calls['played'] == 1