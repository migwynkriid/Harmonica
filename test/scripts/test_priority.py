import sys
import types


def test_set_high_priority_windows(monkeypatch):
    import scripts.priority as pr
    monkeypatch.setattr(sys, 'platform', 'win32', raising=False)
    class Proc:
        def __init__(self):
            self._nice = 0
        def nice(self, val=None):
            if val is None:
                return self._nice
            self._nice = val
            return self._nice
    monkeypatch.setattr(pr.psutil, 'Process', lambda pid: Proc())
    monkeypatch.setattr(pr.psutil, 'HIGH_PRIORITY_CLASS', 128)
    assert pr.set_high_priority() is True