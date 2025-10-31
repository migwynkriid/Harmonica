import sys
import types
import pytest


@pytest.mark.asyncio
async def test_musicbot_get_instance_singleton():
    import scripts.musicbot as mb
    a = mb.MusicBot.get_instance('A')
    b = mb.MusicBot.get_instance('A')
    c = mb.MusicBot.get_instance('B')
    assert a is b
    assert a is not c


@pytest.mark.asyncio
async def test_musicbot_cancel_downloads_disconnects(monkeypatch):
    import scripts.musicbot as mb
    m = mb.MusicBot.get_instance('C')
    # Attach voice client stub
    from test.conftest import StubVoiceClient
    m.voice_client = StubVoiceClient()
    m.queue = [{'url': 'U'}]

    await m.cancel_downloads(disconnect_voice=True)
    assert m.queue == []
    assert m.voice_client.disconnect_called is True
    assert m.current_song is None
    assert m.is_playing is False


@pytest.mark.asyncio
async def test_musicbot_handle_play_command_enqueues(monkeypatch, stub_ctx):
    import scripts.musicbot as mb
    m = mb.MusicBot.get_instance('D')

    # Ensure join works
    async def fake_join(ctx):
        # Provide author.voice.channel.connect hook
        from test.conftest import StubVoiceChannel, StubVoiceState, StubVoiceClient
        ch = StubVoiceChannel(members=[stub_ctx.author])
        stub_ctx.author.voice = StubVoiceState(channel=ch)
        m.voice_client = StubVoiceClient(channel=ch)
        stub_ctx.guild.voice_client = m.voice_client
        return True

    monkeypatch.setattr(m, 'join_voice_channel', fake_join)

    # Avoid sending real messages
    async def fake_update_or_send_message(ctx, embed):
        return types.SimpleNamespace(fetch=lambda: None, delete=lambda: None)
    monkeypatch.setattr(m, 'update_or_send_message', fake_update_or_send_message, raising=False)

    # Provide missing attrs
    stub_ctx.voice_client = None

    await m._handle_play_command(stub_ctx, 'hello world')
    # A download_info should be enqueued
    assert m.download_queue.qsize() == 1
    assert m.last_activity is not None


def test_musicbot_progress_bar():
    import scripts.musicbot as mb
    m = mb.MusicBot.get_instance('E')
    bar = m.create_progress_bar(50)
    assert "50%" in bar
    assert '[' in bar and ']' in bar