import asyncio
import pytest


class StubStatusMsg:
    def __init__(self):
        self.guild = type('G', (), {'id': 7})()
    async def edit(self, embed=None, view=None):
        pass


@pytest.mark.asyncio
async def test_progress_hook_throttle_and_thumbnail(monkeypatch):
    import scripts.downloadprogress as dp
    msg = StubStatusMsg()
    dp_inst = dp.DownloadProgress(status_msg=msg, view=None)
    dp_inst.server_id = 'S'
    dp_inst.message_queues['S'] = asyncio.Queue()
    # Avoid starting updater tasks
    monkeypatch.setattr(dp_inst, 'start_updater', lambda loop=None: None)
    # Control time
    times = [0, 1, 3]
    def fake_time():
        return times.pop(0)
    monkeypatch.setattr(dp, 'time', type('T', (), {'time': staticmethod(fake_time)})())
    # Ensure first call not throttled
    dp_inst.last_update = -10
    d_base = {
        'status': 'downloading',
        'downloaded_bytes': 50,
        'total_bytes': 100,
        'info_dict': {'title': 'T', 'webpage_url': 'http://y', 'thumbnail': 'http://thumb'},
    }
    # First enqueue
    dp_inst.progress_hook(dict(d_base))
    # Second throttled (<2s)
    dp_inst.progress_hook(dict(d_base))
    # Third enqueue (>=2s)
    dp_inst.progress_hook(dict(d_base))

    embeds = []
    while not dp_inst.message_queues['S'].empty():
        embeds.append(await dp_inst.message_queues['S'].get())

    assert len(embeds) == 2
    # Thumbnail set on embed
    assert embeds[0].to_dict().get('thumbnail', {}).get('url') == 'http://thumb'