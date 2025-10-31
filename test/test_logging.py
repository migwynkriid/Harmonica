import sys
import types
from scripts.logging import setup_logging, OutputCapture, get_ytdlp_logger


def test_setup_logging_replaces_stdout(monkeypatch):
    # Avoid importing bot.py in setup_logging
    fake_bot = types.SimpleNamespace(GREEN='', BLUE='', RED='', RESET='')
    monkeypatch.setitem(sys.modules, 'bot', fake_bot)

    setup_logging('INFO')
    assert isinstance(sys.stdout, OutputCapture)
    assert isinstance(sys.stderr, OutputCapture)


def test_get_ytdlp_logger_returns_logger():
    logger = get_ytdlp_logger()
    assert logger.name == 'yt-dlp'