import pytest


@pytest.mark.asyncio
async def test_handle_spotify_url_routes(monkeypatch, stub_ctx):
    import scripts.handle_spotify as hs
    class MB(hs.SpotifyHandler):
        def __init__(self):
            self.sp = object()
    mb = MB()
    # Mock handler methods
    async def t(self, id, ctx, status_msg=None): return {'ok': 'track'}
    async def a(self, id, ctx, status_msg=None): return {'ok': 'album'}
    async def p(self, id, ctx, status_msg=None): return {'ok': 'playlist'}
    monkeypatch.setattr(hs.SpotifyHandler, 'handle_spotify_track', t)
    monkeypatch.setattr(hs.SpotifyHandler, 'handle_spotify_album', a)
    monkeypatch.setattr(hs.SpotifyHandler, 'handle_spotify_playlist', p)

    assert (await mb.handle_spotify_url('https://open.spotify.com/track/123', stub_ctx))['ok'] == 'track'
    assert (await mb.handle_spotify_url('https://open.spotify.com/album/456', stub_ctx))['ok'] == 'album'
    assert (await mb.handle_spotify_url('https://open.spotify.com/playlist/789', stub_ctx))['ok'] == 'playlist'