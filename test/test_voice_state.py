import types
import pytest


@pytest.mark.asyncio
async def test_handle_voice_state_update_leaves_empty(monkeypatch, stub_bot_instance):
    import scripts.voice as voice

    # Prepare stub voice client with empty channel
    from test.conftest import StubVoiceClient, StubVoiceChannel
    empty_channel = StubVoiceChannel(members=[types.SimpleNamespace(bot=True)])
    vc = StubVoiceClient(channel=empty_channel)
    stub_bot_instance.voice_client = vc
    stub_bot_instance.guild_id = '99'
    stub_bot_instance.queue = [{'url': 'U'}]

    # Monkeypatch clear_queue
    calls = {'cleared': False}
    import scripts.clear_queue as cq
    monkeypatch.setattr(cq, 'clear_queue', lambda gid=None: calls.__setitem__('cleared', True))

    # Now trigger
    member = types.SimpleNamespace()
    before = types.SimpleNamespace(channel=empty_channel)
    after = types.SimpleNamespace(channel=empty_channel)

    await voice.handle_voice_state_update(stub_bot_instance, member, before, after)

    # Confirm bot state reset behaviors
    assert stub_bot_instance.is_playing is False
    assert stub_bot_instance.current_song is None
    assert stub_bot_instance.is_playing is False
    assert stub_bot_instance.current_song is None


@pytest.mark.asyncio
async def test_handle_voice_state_update_no_action_when_not_empty(monkeypatch, stub_bot_instance):
    import scripts.voice as voice

    # Prepare voice client with one non-bot member
    from test.conftest import StubVoiceClient, StubVoiceChannel
    member_obj = types.SimpleNamespace(bot=False)
    channel = StubVoiceChannel(members=[member_obj])
    vc = StubVoiceClient(channel=channel)
    stub_bot_instance.voice_client = vc

    member = types.SimpleNamespace()
    before = types.SimpleNamespace(channel=channel)
    after = types.SimpleNamespace(channel=channel)

    await voice.handle_voice_state_update(stub_bot_instance, member, before, after)

    assert vc.disconnect_called is False