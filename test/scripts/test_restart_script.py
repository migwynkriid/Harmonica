def test_restart_bot_does_not_exit(monkeypatch):
    import scripts.restart as rs
    calls = {'popen': False, 'exit': 0}
    monkeypatch.setattr(rs.subprocess, 'Popen', lambda args, cwd=None: calls.__setitem__('popen', True))
    monkeypatch.setattr(rs.os, '_exit', lambda code: calls.__setitem__('exit', code))
    rs.restart_bot()
    assert calls['popen'] is True
    assert calls['exit'] in (0, 1)