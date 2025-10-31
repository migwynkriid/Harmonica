import os
from scripts.commandlogger import CommandLogger


def test_commandlogger_writes(tmp_path):
    logger = CommandLogger()
    logger.log_path = tmp_path / 'commandlog.txt'
    logger.log_command('user', '!ping', 'Guild')
    assert os.path.exists(logger.log_path)
    content = logger.log_path.read_text(encoding='utf-8')
    assert 'user' in content and '!ping' in content and 'Guild' in content