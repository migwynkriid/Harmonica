import sys
import types
from collections import deque
import pytest


@pytest.mark.asyncio
async def test_play_next_reconnect_failure_puts_song_back(monkeypatch, stub_ctx):
    class FakeMusicBot:
        _instances = {}
        def __init__(self):
            from test.conftest import StubVoiceClient
            self.voice_client = StubVoiceClient()
            self.queue = []
            self.current_song = {'title': 'Prev', 'url': 'prev-url'}
            self.now_playing_message = None
            self.was_skipped = False
            self.bot = None
            self.queued_messages = {}
            self.waiting_for_song = False
        @classmethod
        def get_instance(cls, gid):
            if gid not in cls._instances:
                cls._instances[gid] = cls()
            return cls._instances[gid]

    import scripts.play_next as pn
    fake_bot_mod = types.SimpleNamespace(MusicBot=FakeMusicBot)
    monkeypatch.setitem(sys.modules, 'bot', fake_bot_mod)

    # Prepare next song and context
    from test.conftest import StubVoiceChannel, StubVoiceState
    ch = StubVoiceChannel()
    stub_ctx.author.voice = StubVoiceState(channel=ch)
    mb = FakeMusicBot.get_instance('1')
    stub_ctx.guild.voice_client = None  # simulate disconnected
    mb.voice_client._connected = False
    mb.queue.append({'title': 'New', 'url': 'new-url', 'file_path': __file__, 'is_stream': False, 'requester': stub_ctx.author})
    # Provide appendleft on a list-like queue
    class FakeDeque(list):
        def appendleft(self, item):
            self.insert(0, item)
    mb.queue = FakeDeque(mb.queue)

    async def fake_join(ctx):
        return False
    mb.join_voice_channel = fake_join

    await pn.play_next(stub_ctx)
    # Should put song back and leave voice_client None
    assert mb.queue and mb.queue[0]['url'] == 'new-url'
    assert mb.current_song is None or mb.current_song.get('url') != 'new-url'
    assert mb.voice_client is None  # play_next sets voice_client to None on reconnect failure
    # end