import pytest


@pytest.mark.asyncio
async def test_shuffle_queue():
    from scripts.shufflelogic import shuffle_queue
    class MB:
        def __init__(self):
            self.queue = [{'title': 'a'}, {'title': 'b'}, {'title': 'c'}]
    mb = MB()
    res = await shuffle_queue(None, mb)
    assert res is True
    assert len(mb.queue) == 3