import sys
import pytest

import scripts.ffmpeg as ff


def test_check_ffmpeg_in_path_mocked(monkeypatch):
    calls = {'ran': False}

    def fake_run(cmd, capture_output=True, check=True):
        calls['ran'] = True
        return None

    monkeypatch.setattr(ff.subprocess, 'run', fake_run)
    assert ff.check_ffmpeg_in_path() is True
    assert calls['ran'] is True


def test_get_ffmpeg_path_windows(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32', raising=False)
    monkeypatch.setattr(ff, 'check_ffmpeg_in_path', lambda: True)
    assert ff.get_ffmpeg_path() == 'ffmpeg'

    monkeypatch.setattr(ff, 'check_ffmpeg_in_path', lambda: False)
    # Pretend install works
    monkeypatch.setattr(ff, 'install_ffmpeg_windows', lambda: True)
    assert ff.get_ffmpeg_path() == 'ffmpeg'


def test_get_ffmpeg_path_linux(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'linux', raising=False)
    monkeypatch.setattr(ff, 'check_ffmpeg_in_path', lambda: True)
    assert ff.get_ffmpeg_path() == 'ffmpeg'