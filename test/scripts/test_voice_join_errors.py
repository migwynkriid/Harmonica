import types
import pytest


@pytest.mark.asyncio
async def test_join_voice_channel_user_not_in_voice(monkeypatch, stub_ctx):
    import scripts.voice as voice
    # Stub update_or_send_message to avoid actual Discord calls
    msgs = []
    async def fake_update(bot, ctx, embed=None): msgs.append(embed)
    monkeypatch.setattr(voice, 'update_or_send_message', fake_update)

    class MB:
        voice_client = None
    mb = MB()
    # Ensure author.voice is None
    stub_ctx.author.voice = None
    ok = await voice.join_voice_channel(mb, stub_ctx)
    assert ok is False
    assert msgs, "Expected an error embed to be sent"


@pytest.mark.asyncio
async def test_join_voice_channel_empty_channel(monkeypatch, stub_ctx):
    import scripts.voice as voice
    msgs = []
    async def fake_update(bot, ctx, embed=None): msgs.append(embed)
    monkeypatch.setattr(voice, 'update_or_send_message', fake_update)

    # Fake config to enable AUTO_LEAVE_EMPTY
    monkeypatch.setattr(voice, 'get_voice_config', lambda: {'AUTO_LEAVE_EMPTY': True})

    class Member:
        def __init__(self, bot=False): self.bot = bot
    class Ch:
        def __init__(self): self.members = [Member(bot=True)]
        async def connect(self, self_deaf=True): return types.SimpleNamespace(is_connected=lambda: True)
    class VoiceState:
        def __init__(self): self.channel = Ch()
    stub_ctx.author.voice = VoiceState()

    class MB:
        voice_client = None
        last_activity = 0
    ok = await voice.join_voice_channel(MB(), stub_ctx)
    assert ok is False
    assert msgs, "Expected an error embed for empty channel"