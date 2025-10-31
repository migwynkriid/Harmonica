import os
from scripts.paths import (
    get_ytdlp_path,
    get_ffmpeg_path,
    get_ffprobe_path,
    get_root_dir,
    get_downloads_dir,
    get_cache_dir,
    get_cache_file,
    get_absolute_path,
    get_relative_path,
)


def test_root_and_subdirs_exist_strings():
    root = get_root_dir()
    assert isinstance(root, str)
    assert os.path.isabs(root)
    assert os.path.isdir(root)

    downloads = get_downloads_dir()
    assert isinstance(downloads, str)

    cache = get_cache_dir()
    assert isinstance(cache, str)


def test_cache_file_and_path_conversions():
    cf = get_cache_file('test.json')
    assert cf.endswith(os.path.join('.cache', 'test.json'))

    rel = 'scripts/config.py'
    abs_path = get_absolute_path(rel)
    assert os.path.normpath(abs_path).endswith(os.path.normpath(rel))

    # Relative conversion back
    back_rel = get_relative_path(abs_path)
    assert back_rel.endswith(rel.replace('/', os.sep))