import pytest


@pytest.mark.asyncio
async def test_ui_buttons_toggle(monkeypatch):
    import scripts.ui_components as ui
    monkeypatch.setattr(ui, 'load_config', lambda: {'MESSAGES': {'DISCORD_UI_BUTTONS': True}})
    assert ui.should_show_buttons() is True
    assert ui.create_now_playing_view() is not None
    monkeypatch.setattr(ui, 'load_config', lambda: {'MESSAGES': {'DISCORD_UI_BUTTONS': False}})
    assert ui.should_show_buttons() is False
    assert ui.create_now_playing_view() is None