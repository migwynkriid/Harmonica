import json
import os
import importlib
import pytest


@pytest.mark.asyncio
async def test_server_prefixes_file_lifecycle(tmp_path, monkeypatch):
    # Import module and redirect the JSON file path to a temp location
    import scripts.server_prefixes as sp
    tmp_file = tmp_path / 'server_prefixes.json'
    monkeypatch.setattr(sp, 'SERVER_PREFIXES_FILE', str(tmp_file))

    # Sync init creates file
    d = sp.init_server_prefixes_sync()
    assert isinstance(d, dict)
    assert os.path.exists(tmp_file)

    # Async load/save and set/reset behaviors
    prefixes = await sp.load_server_prefixes()
    assert prefixes == {}

    changed = await sp.set_prefix(123, '!')
    assert changed is True
    loaded = await sp.load_server_prefixes()
    assert loaded.get('123') == '!'

    reset = await sp.reset_prefix(123)
    assert reset is True
    loaded2 = await sp.load_server_prefixes()
    assert '123' not in loaded2