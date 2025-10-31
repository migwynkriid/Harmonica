import pytest


@pytest.mark.asyncio
async def test_get_audio_duration_monkeypatched(monkeypatch):
    from scripts import duration as dur
    class Proc:
        def __init__(self):
            self.returncode = 0
        async def communicate(self):
            return (b'{"format": {"duration": "12.34"}}', b'')
    async def fake_exec(*args, **kwargs):
        return Proc()
    monkeypatch.setattr(dur.asyncio, 'create_subprocess_exec', fake_exec)
    d = await dur.get_audio_duration('a.m4a')
    assert abs(d - 12.34) < 1e-6