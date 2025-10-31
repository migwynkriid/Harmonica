import asyncio
import pytest


@pytest.mark.asyncio
async def test_musicbot_process_download_queue(monkeypatch, stub_ctx):
    import scripts.musicbot as mb
    calls = {'played': 0}
    async def fake_play_next(ctx):
        calls['played'] += 1
    import scripts.play_next as pn
    monkeypatch.setattr(pn, 'play_next', fake_play_next)
    import scripts.musicbot as mb_mod
    monkeypatch.setattr(mb_mod, 'play_next', fake_play_next)

    # Get instance and stub download_song
    inst = mb.MusicBot.get_instance('proc')
    # Ensure any 'bot' module import points to the real class
    import sys, types
    sys.modules['bot'] = types.SimpleNamespace(MusicBot=mb.MusicBot)
    # Provide minimal bot attribute expected by process_download_queue
    inst.bot = types.SimpleNamespace(get_cog=lambda name: None)
    # Provide a connected voice client and not playing state
    from test.conftest import StubVoiceClient, StubVoiceChannel, StubVoiceState
    vc_channel = StubVoiceChannel()
    inst.voice_client = StubVoiceClient(channel=vc_channel)
    inst.is_playing = False
    inst.waiting_for_song = False
    # Ensure ctx author appears in a voice channel
    stub_ctx.author.voice = StubVoiceState(channel=vc_channel)
    async def fake_download_song(query, status_msg=None, ctx=None, skip_url_check=False):
        return {'title': 't', 'url': 'u', 'file_path': __file__, 'thumbnail': None}
    monkeypatch.setattr(inst, 'download_song', fake_download_song)

    # Enqueue one download task
    await inst.download_queue.put({'query': 'q', 'ctx': stub_ctx, 'status_msg': None})

    task = asyncio.create_task(inst.process_download_queue())
    # Give it a moment to process
    await asyncio.sleep(0.2)
    # Cancel the infinite loop task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert inst.queue and inst.queue[0]['title'] == 't'
    assert calls['played'] >= 1