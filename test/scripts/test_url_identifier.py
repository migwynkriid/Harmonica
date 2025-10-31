import types
import pytest


def test_is_url_and_playlist_channel():
    from scripts.url_identifier import is_url, is_playlist_url, is_youtube_channel
    assert is_url('https://example.com') is True
    assert is_playlist_url('https://www.youtube.com/playlist?list=ABC') is True
    assert is_youtube_channel('https://www.youtube.com/@someone') is True


def test_is_radio_stream_monkeypatched(monkeypatch):
    from scripts import url_identifier as ui
    class Resp:
        headers = {'Content-Type': 'audio/mpeg'}
    monkeypatch.setattr(ui.requests, 'head', lambda url, allow_redirects=True, timeout=5: Resp())
    assert ui.is_radio_stream('http://radio.example') is True