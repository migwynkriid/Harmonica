import sys
import importlib
import types
import pytest


@pytest.mark.asyncio
async def test_load_config_keys(monkeypatch):
    # Ensure paths functions return simple values to avoid external calls
    import scripts.paths as p
    monkeypatch.setattr(p, 'get_ffmpeg_path', lambda: 'ffmpeg')
    monkeypatch.setattr(p, 'get_ffprobe_path', lambda: 'ffprobe')
    monkeypatch.setattr(p, 'get_ytdlp_path', lambda: 'yt-dlp')

    # Reload config to pick up monkeypatched paths
    if 'scripts.config' in sys.modules:
        del sys.modules['scripts.config']
    cfg = importlib.import_module('scripts.config')

    assert isinstance(cfg.config_vars, dict)
    for key in ['OWNER_ID', 'PREFIX', 'LOG_LEVEL', 'VOICE', 'DOWNLOADS', 'MESSAGES', 'PERMISSIONS']:
        assert key in cfg.config_vars

    # Verify FFMPEG_OPTIONS contains executable and options
    assert 'executable' in cfg.FFMPEG_OPTIONS
    assert isinstance(cfg.FFMPEG_OPTIONS['options'], str)