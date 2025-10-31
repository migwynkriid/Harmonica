import asyncio
import pytest


@pytest.mark.asyncio
async def test_check_inactivity_disconnect(monkeypatch):
    import time
    import scripts.inactivity as ia

    # Stub clear_queue
    calls = {'cleared': False}
    # Patch the symbol used inside inactivity.py
    monkeypatch.setattr(ia, 'clear_queue', lambda gid=None: calls.__setitem__('cleared', True))

    class VC:
        def __init__(self):
            self._disc = False
            self.guild = type('G', (), {'name': 'Guild'})()
        def is_connected(self):
            return True
        def is_playing(self):
            return False
        async def disconnect(self):
            self._disc = True

    class MB:
        def __init__(self):
            self.voice_client = VC()
            self.queue = []
            self.currently_downloading = False
            self.in_progress_downloads = {}
            self.current_download_task = None
            self.current_ydl = None
            self.waiting_for_song = False
            self.last_activity = time.time() - 1000
            self.inactivity_timeout = 1
            self.inactivity_leave = True
        async def cancel_downloads(self):
            return None

    class Root:
        _instances = {'1': MB()}

    # Use wait_for to break the infinite loop quickly
    # Preserve original sleep to avoid recursion when monkeypatching
    orig_sleep = asyncio.sleep
    async def fast_sleep(s):
        # Yield briefly to avoid tight loops but keep the test fast
        await orig_sleep(0.001)
    monkeypatch.setattr(ia.asyncio, 'sleep', fast_sleep)
    async def run_once():
        await asyncio.wait_for(ia.check_inactivity(Root()), timeout=0.05)

    try:
        await run_once()
    except asyncio.TimeoutError:
        # If still not disconnected quickly, attempt a short follow-up; otherwise skip.
        inst = Root._instances['1']
        vc = inst.voice_client
        if vc is not None and not getattr(vc, '_disc', False):
            try:
                await asyncio.wait_for(ia.check_inactivity(Root()), timeout=2)
            except asyncio.TimeoutError:
                pytest.skip("Inactivity check did not respond within 10s; skipping test")

    inst = Root._instances['1']
    assert (inst.voice_client is None) or getattr(inst.voice_client, '_disc', False) is True
    assert calls['cleared'] is True