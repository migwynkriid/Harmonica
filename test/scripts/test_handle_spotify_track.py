import types
import pytest


@pytest.mark.asyncio
async def test_handle_spotify_track_cached(monkeypatch, stub_ctx):
    import scripts.handle_spotify as hs
    from scripts import caching as caching

    class MB(hs.SpotifyHandler):
        def __init__(self):
            self.sp = object()
            self.queue = []
            self.queued_messages = {}
            self.current_song = None
            self.is_playing = False
            self.voice_client = types.SimpleNamespace(is_playing=lambda: False, is_connected=lambda: True)
            self.waiting_for_song = False

    mb = MB()

    cached = {
        'file_path': __file__,
        'title': 'CachedTitle',
        'url': 'https://open.spotify.com/track/ID',
        'thumbnail': None,
    }

    monkeypatch.setattr(caching.playlist_cache, 'get_cached_spotify_track', lambda tid: cached)

    async def fake_duration(fp):
        return 12.34
    monkeypatch.setattr(hs, 'get_audio_duration', fake_duration)

    calls = {'proc': 0}
    async def fake_process_queue(music_bot):
        calls['proc'] += 1
    monkeypatch.setattr(hs, 'process_queue', fake_process_queue)

    # Ensure ctx has a bot with get_cog
    stub_ctx.bot = types.SimpleNamespace(get_cog=lambda name: None)

    res = await mb.handle_spotify_track('ID', stub_ctx, status_msg=None)
    assert res and res['title'] == 'CachedTitle'
    assert calls['proc'] == 1


@pytest.mark.asyncio
async def test_handle_spotify_track_search_flow(monkeypatch, stub_ctx):
    import scripts.handle_spotify as hs
    from scripts import caching as caching
    import asyncio
    import yt_dlp

    class MB(hs.SpotifyHandler):
        def __init__(self):
            self.sp = types.SimpleNamespace(track=lambda tid: {'artists': [{'name': 'Artist'}], 'name': 'Track'})
            self.queue = []
            self.queued_messages = {}
            self.current_song = None
            self.is_playing = False
            self.voice_client = types.SimpleNamespace(is_playing=lambda: False, is_connected=lambda: True)
            self.waiting_for_song = False

        async def download_song(self, url, status_msg=None, ctx=None):
            return {'title': 'Downloaded', 'url': url, 'file_path': __file__, 'thumbnail': None}

    mb = MB()

    # No cache
    monkeypatch.setattr(caching.playlist_cache, 'get_cached_spotify_track', lambda tid: None)

    # Fake loop run_in_executor to return search info immediately
    class DummyAwaitable:
        def __init__(self, result):
            self._result = result
        def __await__(self):
            async def _():
                return self._result
            return _().__await__()

    class FakeLoop:
        def run_in_executor(self, executor, func):
            info = {'entries': [{'url': 'http://yt.video', 'webpage_url': 'http://yt.video'}]}
            return DummyAwaitable(info)

    monkeypatch.setattr(asyncio, 'get_event_loop', lambda: FakeLoop())

    # Stub YoutubeDL context manager
    class FakeYDL:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def extract_info(self, query, download=False):
            # Not used directly due to run_in_executor stub
            return {'entries': [{'url': 'http://yt.video'}]}
    monkeypatch.setattr(yt_dlp, 'YoutubeDL', lambda opts: FakeYDL())

    calls = {'proc': 0}
    async def fake_process_queue(music_bot):
        calls['proc'] += 1
    monkeypatch.setattr(hs, 'process_queue', fake_process_queue)

    stub_ctx.bot = types.SimpleNamespace(get_cog=lambda name: None)

    async def fake_duration(fp):
        return 12.34
    monkeypatch.setattr(hs, 'get_audio_duration', fake_duration)
    res = await mb.handle_spotify_track('ID', stub_ctx, status_msg=None)
    assert res and res['title'] == 'Downloaded'
    assert calls['proc'] == 1