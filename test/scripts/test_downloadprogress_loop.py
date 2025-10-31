import asyncio
import pytest


class StubStatusMsg:
    def __init__(self):
        self.guild = type('G', (), {'id': 42})()
        self.edits = []
    async def edit(self, embed=None, view=None):
        self.edits.append(embed)


@pytest.mark.asyncio
async def test_downloadprogress_updater_processes_queue(monkeypatch):
    import scripts.downloadprogress as dp
    # Speed up updater sleeps
    async def fast_sleep(s):
        return None
    monkeypatch.setattr(dp.asyncio, 'sleep', fast_sleep)
    from scripts.downloadprogress import DownloadProgress
    msg = StubStatusMsg()
    dp = DownloadProgress(status_msg=msg, view=None)
    dp.server_id = '42'
    dp.message_queues['42'] = asyncio.Queue()
    dp.download_complete = True

    # Put one embed to process
    class E: pass
    await dp.message_queues['42'].put(E())

    # Run updater and wait for it to consume
    await dp._message_updater('42')
    assert msg.edits and isinstance(msg.edits[0], E)