import pytest


class DummyMsg:
    async def delete(self):
        self.deleted = True
    async def edit(self, embed=None, view=None):
        self.edited = True


class DummyVoiceClient:
    def __init__(self):
        self._connected = True
        self._playing = False
        self.guild = type('G', (), {'name': 'Guild'})()
    def is_connected(self):
        return self._connected
    def is_playing(self):
        return self._playing


@pytest.mark.asyncio
async def test_after_playing_coro_calls_play_next(monkeypatch):
    from scripts.after_playing_coro import AfterPlayingHandler
    calls = {'play_next': 0}
    async def fake_play_next(ctx):
        calls['play_next'] += 1
    import scripts.play_next as pn
    import scripts.after_playing_coro as apc
    monkeypatch.setattr(pn, 'play_next', fake_play_next)
    monkeypatch.setattr(apc, 'play_next', fake_play_next)

    class H(AfterPlayingHandler):
        def __init__(self):
            self.playback_state = 'playing'
            import asyncio
            self.download_queue = asyncio.Queue()
            self.currently_downloading = False
            self.queue = [{'title': 't', 'url': 'u', 'ctx': type('C', (), {'guild': object()})()}]
            self.current_song = self.queue[0]
            self.bot = type('B', (), {})()
            self.voice_client = DummyVoiceClient()
            self.now_playing_message = DummyMsg()
    h = H()
    # Avoid importing real bot module inside play_next
    import sys, types
    class FakeMB:
        _instances = {}
        @classmethod
        def get_instance(cls, gid):
            return type('I', (), {'queue': [], 'current_song': None, 'queued_messages': {}, 'voice_client': type('VC', (), {'is_connected': lambda self: False})()})()
    sys.modules['bot'] = types.SimpleNamespace(MusicBot=FakeMB)
    await h.after_playing_coro(None, type('CTX', (), {'guild': object()})())
    assert calls['play_next'] == 1