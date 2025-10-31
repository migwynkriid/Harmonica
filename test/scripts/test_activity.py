import pytest


class DummyBot:
    def __init__(self):
        self.presences = []
        self.guilds = [object(), object()]
    async def change_presence(self, *, activity=None):
        self.presences.append(activity)


@pytest.mark.asyncio
async def test_update_activity_shows_song(monkeypatch):
    import scripts.activity as act
    bot = DummyBot()
    monkeypatch.setitem(act.config_vars, 'SHOW_ACTIVITY_STATUS', True)
    song = {'title': 'Test Song'}
    await act.update_activity(bot, current_song=song, is_playing=True)
    assert bot.presences and bot.presences[-1].name == 'Test Song'


@pytest.mark.asyncio
async def test_update_activity_shows_server_count(monkeypatch):
    import scripts.activity as act
    bot = DummyBot()
    monkeypatch.setitem(act.config_vars, 'SHOW_ACTIVITY_STATUS', False)
    await act.update_activity(bot, current_song=None, is_playing=False)
    assert bot.presences and 'servers' in bot.presences[-1].name