import os
import pytest


def test_clear_downloads_folder_respects_config(tmp_path, monkeypatch):
    from scripts import cleardownloads as cd
    # Point CWD to temp
    monkeypatch.setattr(os, 'getcwd', lambda: str(tmp_path))
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    f = downloads / 'file.txt'
    f.write_text('data')
    # Disable auto clear
    monkeypatch.setattr(cd, 'get_config', lambda: False)
    cd.clear_downloads_folder()
    assert f.exists()
    # Enable auto clear
    monkeypatch.setattr(cd, 'get_config', lambda: True)
    cd.clear_downloads_folder()
    assert not f.exists()