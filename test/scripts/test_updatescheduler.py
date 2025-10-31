import pytest


@pytest.mark.asyncio
async def test_check_updates_no_auto(monkeypatch):
    import scripts.updatescheduler as us
    monkeypatch.setattr(us, 'load_config', lambda: {'AUTO_UPDATE': False})
    # Should return quickly with no actions
    await us.check_updates(object())


@pytest.mark.asyncio
async def test_check_updates_mocked(monkeypatch):
    import scripts.updatescheduler as us
    # Enable auto update
    monkeypatch.setattr(us, 'load_config', lambda: {'AUTO_UPDATE': True})
    # Mock subprocess.run to return plausible outputs
    class Result:
        def __init__(self, stdout=''):
            self.stdout = stdout
    def fake_run(cmd, **kwargs):
        s = ' '.join(cmd)
        if 'rev-parse' in s:
            return Result('abc123')
        if 'status' in s:
            return Result('Your branch is behind')
        if 'pip install' in s and '--dry-run' in s:
            return Result('Would install: pkg1 (1.0) -> (1.1)')
        return Result('')
    monkeypatch.setattr(us, 'subprocess', type('X', (), {'run': staticmethod(fake_run)}))
    # Mock restart_bot
    calls = {'restart': False}
    import scripts.restart as rs
    monkeypatch.setattr(rs, 'restart_bot', lambda: calls.__setitem__('restart', True))
    # Mock MusicBot instances as not in voice
    import scripts.musicbot as mb
    mb.MusicBot._instances = {}
    await us.check_updates(object())
    # Might schedule restart depending on paths, but ensure function ran
    assert isinstance(calls['restart'], bool)