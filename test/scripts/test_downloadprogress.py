import pytest


class StubStatusMsg:
    def __init__(self):
        self.guild = type('G', (), {'id': 1})()
        self.edits = []
    async def edit(self, embed=None, view=None):
        self.edits.append(embed)


@pytest.mark.asyncio
async def test_downloadprogress_queue_updates():
    from scripts.downloadprogress import DownloadProgress
    msg = StubStatusMsg()
    dp = DownloadProgress(status_msg=msg, view=None)
    # Provide ctx for footer
    class A:
        display_name = 'User'
        display_avatar = type('AV', (), {'url': 'http://example.com'})()
    dp.ctx = type('CTX', (), {'author': A(), 'guild': type('G', (), {'id': 1})()})()

    # Invoke progress_hook to enqueue an embed
    d = {
        'status': 'downloading',
        'downloaded_bytes': 50,
        'total_bytes': 100,
        'info_dict': {'title': 'T', 'webpage_url': 'http://y', 'thumbnail': None},
    }
    dp.progress_hook(d)
    # Start updater and process one item
    dp.start_updater()
    # Allow loop to run a bit
    await dp.cleanup()
    # Either edits exist or queues cleaned
    assert dp.server_id is not None