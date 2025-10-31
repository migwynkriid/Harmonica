import pytest


@pytest.mark.asyncio
async def test_spotify_process_tracks_cached_and_uncached(monkeypatch, stub_ctx):
    import scripts.handle_spotify as hs
    from scripts import caching as caching
    import asyncio

    # Patch playlist_cache behaviors
    cached_ids = {'c1'}
    def fake_get_cached(track_id):
        if track_id in cached_ids:
            return {'file_path': __file__, 'title': f'Cached-{track_id}', 'url': f'https://open.spotify.com/track/{track_id}', 'thumbnail': None}
        return None
    caching.playlist_cache.get_cached_spotify_track = fake_get_cached
    added = []
    caching.playlist_cache.add_spotify_track = lambda tid, fp, title=None, thumbnail=None, artist=None, skip_save=False: added.append((tid, fp))
    monkeypatch.setattr(asyncio, 'sleep', lambda s: asyncio.sleep(0))

    async def fake_duration(fp):
        return 2.0
    monkeypatch.setattr(hs, 'get_audio_duration', fake_duration)

    class MB(hs.SpotifyHandler):
        def __init__(self):
            self.queue = []
            self.is_playing = False
            self.voice_client = type('VC', (), {'is_playing': lambda self: False})()
        async def download_song(self, query, status_msg=None, ctx=None):
            # produce a fake song
            return {'title': 'DL', 'url': 'http://yt', 'file_path': __file__, 'thumbnail': None}

    mb = MB()
    tracks = [
        {'id': 'c1', 'name': 'N1', 'artists': [{'name': 'A'}]},
        {'id': 'u1', 'name': 'N2', 'artists': [{'name': 'B'}]},
    ]
    # Intercept process_queue within handle_spotify module
    calls = {'proc': 0}
    async def fake_process_queue(music_bot): calls['proc'] += 1
    monkeypatch.setattr(hs, 'process_queue', fake_process_queue)

    await mb._process_spotify_tracks(tracks, stub_ctx, status_msg=None, source_name='Playlist')

    # One cached + one uncached queued
    assert len(mb.queue) == 2
    # Uncached track was cached via add_spotify_track
    assert any(tid == 'u1' for (tid, fp) in added)
    assert calls['proc'] >= 1