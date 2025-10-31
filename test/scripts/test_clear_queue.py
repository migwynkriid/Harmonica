import pytest


@pytest.mark.asyncio
async def test_clear_queue_specific(monkeypatch):
    import scripts.clear_queue as cq
    class MB:
        def __init__(self):
            import asyncio
            self.queue = ['a', 'b']
            self.download_queue = asyncio.Queue()
            self.download_queue.put_nowait(1)
            self.download_queue.put_nowait(2)
    import scripts.musicbot as mb
    mb.MusicBot._instances = {'1': MB()}
    # Create bot module alias used by clear_queue
    import sys
    sys.modules['bot'] = mb
    cq.clear_queue('1')
    assert mb.MusicBot._instances['1'].queue == []
    assert mb.MusicBot._instances['1'].download_queue.empty()


def test_clear_queue_all(monkeypatch):
    import scripts.clear_queue as cq
    class MB:
        def __init__(self):
            import asyncio
            self.queue = ['x']
            self.download_queue = asyncio.Queue()
            self.download_queue.put_nowait(5)
    import scripts.musicbot as mb
    mb.MusicBot._instances = {'1': MB(), '2': MB()}
    import sys
    sys.modules['bot'] = mb
    cq.clear_queue()
    assert all(inst.queue == [] for inst in mb.MusicBot._instances.values())