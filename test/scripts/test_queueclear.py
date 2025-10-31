import pytest


@pytest.mark.asyncio
async def test_clear_queue_command_remove_position(monkeypatch, stub_ctx):
    from scripts.queueclear import clear_queue_command
    class MB:
        def __init__(self):
            self.queue = [{'title': 'a'}, {'title': 'b'}]
            self.download_queue = __import__('asyncio').Queue()
    stub_ctx.voice_client = object()
    mb = MB()
    await clear_queue_command(stub_ctx, mb, position=1)
    # Check that a message was sent
    assert stub_ctx._sent and 'Song Removed' in stub_ctx._sent[-1].embed.title