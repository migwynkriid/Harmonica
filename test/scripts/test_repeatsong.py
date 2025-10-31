import pytest


@pytest.mark.asyncio
async def test_repeat_song_adds_current():
    from scripts.repeatsong import repeat_song
    class MB:
        def __init__(self):
            self.current_song = {'title': 't'}
            self.queue = []
    mb = MB()
    res = await repeat_song(mb, None)
    assert res is True
    assert mb.queue and mb.queue[-1]['title'] == 't'