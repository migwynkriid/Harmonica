import os
import types
import pytest


@pytest.mark.asyncio
async def test_process_queue_missing_file(monkeypatch, stub_ctx):
    import scripts.process_queue as pq
    class VC:
        def is_connected(self): return True
        def is_playing(self): return False
        def play(self, *a, **kw): pass
        def stop(self): pass
    class MB:
        def __init__(self):
            self.queue = [{'title': 't', 'url': 'u', 'file_path': 'nonexistent.file', 'is_stream': False, 'ctx': stub_ctx}]
            self.voice_client = VC()
            self.waiting_for_song = False
            self.is_playing = False
            self.queued_messages = {}
            self.bot = None
        async def after_playing_coro(self, e, ctx): pass
        bot_loop = None
        last_known_ctx = None
        join_voice_channel = None
    mb = MB()
    await pq.process_queue(mb, stub_ctx)
    # Queue should now be empty after skipping missing file
    assert mb.queue == []


@pytest.mark.asyncio
async def test_process_queue_stream_handling(monkeypatch, stub_ctx):
    import scripts.process_queue as pq
    import discord
    class FakeAudio:
        def __init__(self, *a, **kw): pass
        def read(self): pass
    monkeypatch.setattr(discord, 'FFmpegPCMAudio', FakeAudio)
    # Provide a safe transformer with "original" and cleanup to avoid destructor warnings
    class SafeTransformer:
        def __init__(self, original, volume=1.0):
            self.original = original
        def cleanup(self):
            pass
    monkeypatch.setattr(discord, 'PCMVolumeTransformer', SafeTransformer)
    class VC:
        def is_connected(self): return True
        def is_playing(self): return False
        def play(self, *a, **kw): self._played = True
        def stop(self): pass
    class MB:
        def __init__(self):
            self.queue = [{'title': 'stream', 'url': 's', 'file_path': 'http://stream.example', 'is_stream': True, 'ctx': stub_ctx}]
            self.voice_client = VC()
            self.waiting_for_song = False
            self.is_playing = False
            self.queued_messages = {}
            self.bot = None
            self.playback_state = None
        async def after_playing_coro(self, e, ctx): pass
        bot_loop = None
        last_known_ctx = None
        join_voice_channel = None
        now_playing_message = None
    mb = MB()
    await pq.process_queue(mb, stub_ctx)
    assert mb.playback_state == 'playing'


@pytest.mark.asyncio
async def test_process_queue_presence_update_failure(monkeypatch, stub_ctx):
    import scripts.process_queue as pq
    import scripts.activity as act
    async def bad_update(bot, song, is_playing=False): raise RuntimeError('presence fail')
    monkeypatch.setattr(act, 'update_activity', bad_update)
    class VC:
        def is_connected(self): return True
        def is_playing(self): return False
        def play(self, *a, **kw): pass
        def stop(self): pass
    class MB:
        def __init__(self):
            self.queue = [{'title': 't', 'url': 'u', 'file_path': __file__, 'is_stream': False, 'ctx': stub_ctx}]
            self.voice_client = VC()
            self.waiting_for_song = False
            self.is_playing = False
            self.queued_messages = {}
            self.bot = types.SimpleNamespace()
        async def after_playing_coro(self, e, ctx): pass
        bot_loop = None
        last_known_ctx = None
        join_voice_channel = None
        now_playing_message = None
    mb = MB()
    await pq.process_queue(mb, stub_ctx)
    # Should not crash and should set playing state
    assert mb.is_playing is True