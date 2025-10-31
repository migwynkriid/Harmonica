import pytest


@pytest.mark.asyncio
async def test_voice_checks_valid(monkeypatch, stub_ctx):
    from scripts.voice_checks import check_voice_state
    # Stub music_bot with voice_client channel
    class MB:
        def __init__(self, channel):
            self.voice_client = types.SimpleNamespace(channel=channel)
            self.current_song = None
            self.is_playing = False
    import types
    from test.conftest import StubVoiceChannel, StubVoiceState
    ch = StubVoiceChannel()
    stub_ctx.author.voice = StubVoiceState(channel=ch)
    mb = MB(ch)
    valid, embed = await check_voice_state(stub_ctx, mb)
    assert valid is True
    assert embed is None


@pytest.mark.asyncio
async def test_voice_checks_mismatch(monkeypatch, stub_ctx):
    from scripts.voice_checks import check_voice_state
    import types
    from test.conftest import StubVoiceChannel, StubVoiceState
    ch_bot = StubVoiceChannel(name="Bot")
    ch_user = StubVoiceChannel(name="User")
    stub_ctx.author.voice = StubVoiceState(channel=ch_user)
    mb = types.SimpleNamespace(voice_client=types.SimpleNamespace(channel=ch_bot), current_song=None, is_playing=False)
    valid, embed = await check_voice_state(stub_ctx, mb)
    assert valid is False
    assert embed is not None