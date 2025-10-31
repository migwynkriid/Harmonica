import os
import types
import pytest


@pytest.mark.asyncio
async def test_process_queue_plays_audio(monkeypatch, tmp_path, stub_bot_instance, stub_ctx):
    # Prepare a fake audio file
    f = tmp_path / "song.m4a"
    f.write_text("fake")

    # Monkeypatch discord audio classes
    class FakeAudio:
        def __init__(self, *a, **kw):
            self.read_called = False
        def read(self):
            self.read_called = True
    class FakeVol:
        def __init__(self, src, volume=1.0):
            self.src = src

    import scripts.process_queue as pq
    import discord
    monkeypatch.setattr(discord, 'FFmpegPCMAudio', FakeAudio)
    monkeypatch.setattr(discord, 'PCMVolumeTransformer', FakeVol)

    # Attach a stub voice client
    from test.conftest import StubVoiceClient
    vc = StubVoiceClient()
    stub_bot_instance.voice_client = vc

    # Queue one song
    stub_bot_instance.queue.append({
        'title': 'T',
        'url': 'U',
        'file_path': str(f),
        'thumbnail': None,
        'ctx': stub_ctx,
        'requester': stub_ctx.author,
        'is_stream': False,
    })

    await pq.process_queue(stub_bot_instance, ctx=stub_ctx)

    assert vc.is_playing() is True
    assert stub_bot_instance.current_song['title'] == 'T'
    assert stub_bot_instance.now_playing_message is not None


@pytest.mark.asyncio
async def test_play_next_plays_audio(monkeypatch, tmp_path, stub_ctx):
    # Prepare fake classes to stand-in for bot.MusicBot
    class FakeMusicBot:
        _instances = {}
        def __init__(self):
            from test.conftest import StubVoiceClient
            self.voice_client = StubVoiceClient()
            self.queue = []
            self.queued_messages = {}
            self.bot_loop = None
            self.current_song = None
            self.bot = None
            self.now_playing_message = None

        @classmethod
        def get_instance(cls, gid):
            if gid not in cls._instances:
                cls._instances[gid] = cls()
            return cls._instances[gid]

    # Install fake bot module
    import sys
    fake_bot_mod = types.SimpleNamespace(MusicBot=FakeMusicBot)
    monkeypatch.setitem(sys.modules, 'bot', fake_bot_mod)

    # Monkeypatch audio
    class FakeAudio:
        def __init__(self, *a, **kw):
            self.read_called = False
        def read(self):
            self.read_called = True
    import scripts.play_next as pn
    import discord
    monkeypatch.setattr(discord, 'FFmpegPCMAudio', FakeAudio)

    # Create fake file
    f = tmp_path / 'song.m4a'
    f.write_text('fake')

    mb = FakeMusicBot.get_instance('1')
    mb.queue.append({
        'title': 'T2',
        'url': 'U2',
        'file_path': str(f),
        'thumbnail': None,
        'requester': stub_ctx.author,
        'is_stream': False,
    })

    # Provide guild on ctx
    # Attach author voice state channel to let join succeed if needed
    from test.conftest import StubVoiceChannel, StubVoiceState
    vc = StubVoiceChannel(members=[stub_ctx.author])
    stub_ctx.author.voice = StubVoiceState(channel=vc)
    stub_ctx.guild.voice_client = mb.voice_client

    await pn.play_next(stub_ctx)
    assert mb.voice_client.is_playing() is True
    assert mb.current_song['title'] == 'T2'