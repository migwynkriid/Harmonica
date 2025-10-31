import os
import pytest
from scripts import ytdlp


def test_get_ytdlp_path_prefers_local(monkeypatch):
    local_path = os.path.join(os.getcwd(), 'yt-dlp')
    monkeypatch.setattr(os.path, 'exists', lambda p: p == local_path)
    assert ytdlp.get_ytdlp_path() == local_path


def test_get_ytdlp_path_falls_back(monkeypatch):
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    assert ytdlp.get_ytdlp_path() == 'yt-dlp'