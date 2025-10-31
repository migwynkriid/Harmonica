import types
import pytest


@pytest.mark.asyncio
async def test_handle_spotify_album_first_track(monkeypatch, stub_ctx):
    import scripts.handle_spotify as hs
    from scripts import caching as caching

    class MB(hs.SpotifyHandler):
        def __init__(self):
            # Fake spotify client with album and pagination
            self.sp = types.SimpleNamespace(
                album=lambda aid: {'name': 'Album', 'images': [{'url': 'http://img'}]},
                album_tracks=lambda aid: {'items': [{'id': 't1', 'name': 'Song1', 'artists': [{'name': 'Artist'}]}], 'next': None},
                next=lambda results: {'items': [], 'next': None},
            )
            self.queue = []
            self.queued_messages = {}
            self.current_song = None
            self.is_playing = False
            self.voice_client = types.SimpleNamespace(is_playing=lambda: False, is_connected=lambda: True)
            self.waiting_for_song = False

        async def download_song(self, query, status_msg=None, ctx=None):
            return {'title': 'Downloaded', 'url': 'http://yt', 'file_path': __file__, 'thumbnail': None}

    mb = MB()
    # No cache
    monkeypatch.setattr(caching.playlist_cache, 'get_cached_spotify_track', lambda tid: None)
    # Intercept process_queue within handle_spotify module
    calls = {'proc': 0}
    async def fake_process_queue(music_bot): calls['proc'] += 1
    monkeypatch.setattr(hs, 'process_queue', fake_process_queue)
    # Duration
    async def fake_duration(fp): return 10.0
    monkeypatch.setattr(hs, 'get_audio_duration', fake_duration)

    res = await mb.handle_spotify_album('ALB', stub_ctx, status_msg=None)
    assert res and res['title'] in ('Downloaded', 'CachedTitle')
    assert mb.queue and mb.queue[0]['is_from_playlist'] is True
    assert calls['proc'] == 1


@pytest.mark.asyncio
async def test_handle_spotify_playlist_first_track(monkeypatch, stub_ctx):
    import scripts.handle_spotify as hs
    from scripts import caching as caching

    # Build playlist structure with one local skipped and one valid track
    tracks_page = {
        'items': [
            {'track': {'id': None, 'is_local': True}},
            {'track': {'id': 'v1', 'name': 'SongP', 'artists': [{'name': 'Artist'}]}}
        ],
        'next': None,
    }
    playlist_obj = {
        'name': 'Playlist',
        'images': [{'url': 'http://img'}],
        'tracks': tracks_page,
    }

    class MB(hs.SpotifyHandler):
        def __init__(self):
            self.sp = types.SimpleNamespace(
                playlist=lambda pid: playlist_obj,
                next=lambda results: {'items': [], 'next': None},
            )
            self.queue = []
            self.queued_messages = {}
            self.current_song = None
            self.is_playing = False
            self.voice_client = types.SimpleNamespace(is_playing=lambda: False, is_connected=lambda: True)
            self.waiting_for_song = False

        async def download_song(self, query, status_msg=None, ctx=None):
            return {'title': 'DownloadedP', 'url': 'http://ytp', 'file_path': __file__, 'thumbnail': None}

    mb = MB()
    # No cache
    monkeypatch.setattr(caching.playlist_cache, 'get_cached_spotify_track', lambda tid: None)
    # Intercept process_queue within handle_spotify module
    calls = {'proc': 0}
    async def fake_process_queue(music_bot): calls['proc'] += 1
    monkeypatch.setattr(hs, 'process_queue', fake_process_queue)
    # Duration
    async def fake_duration(fp): return 11.0
    monkeypatch.setattr(hs, 'get_audio_duration', fake_duration)

    res = await mb.handle_spotify_playlist('PL', stub_ctx, status_msg=None)
    assert res and res['title'] in ('DownloadedP', 'CachedTitle')
    assert mb.queue and mb.queue[0]['is_from_playlist'] is True
    assert calls['proc'] == 1