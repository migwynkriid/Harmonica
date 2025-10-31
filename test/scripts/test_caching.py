import pytest


def test_playlistcache_valid_id(monkeypatch):
    import scripts.caching as caching
    # Avoid heavy __init__ side effects
    def fake_init(self):
        pass
    monkeypatch.setattr(caching.PlaylistCache, '__init__', fake_init)
    pc = caching.PlaylistCache()
    assert pc._is_valid_youtube_id('abcdefghijk') is True
    assert pc._is_valid_youtube_id('invalid') is False