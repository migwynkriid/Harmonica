import asyncio
import pytest


@pytest.mark.asyncio
async def test_start_inactivity_checker_schedules(monkeypatch):
    import scripts.inactivity as ia
    called = {'ran': False}
    async def fake_check(bot_instance):
        called['ran'] = True
    monkeypatch.setattr(ia, 'check_inactivity', fake_check)

    class MB:
        def __init__(self):
            self.bot_loop = asyncio.get_event_loop()
            self._inactivity_task = None

    mb = MB()
    await ia.start_inactivity_checker(mb)
    assert called['ran'] is True
    assert mb._inactivity_task is not None
    # Cleanup
    mb._inactivity_task.cancel()