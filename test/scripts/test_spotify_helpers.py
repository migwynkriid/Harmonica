import pytest


@pytest.mark.asyncio
async def test_spotify_helpers(monkeypatch):
    import scripts.spotify as spm
    class FakeSP:
        def track(self, tid):
            return {'artists': [{'name': 'Artist'}], 'name': 'Track'}
        def album_tracks(self, aid):
            return {'items': [{'artists': [{'name': 'A'}], 'name': 'T'}]}
        def playlist_tracks(self, pid):
            return {'items': [{'track': {'artists': [{'name': 'B'}], 'name': 'U'}}]}
    monkeypatch.setattr(spm, 'sp', FakeSP())

    name, tid = await spm.get_spotify_track_details('https://open.spotify.com/track/123')
    assert 'Artist - Track' == name and tid == '123'

    album = await spm.get_spotify_album_details('https://open.spotify.com/album/456')
    assert album and 'A - T' in album[0]

    playlist = await spm.get_spotify_playlist_details('https://open.spotify.com/playlist/789')
    assert playlist and 'B - U' in playlist[0]