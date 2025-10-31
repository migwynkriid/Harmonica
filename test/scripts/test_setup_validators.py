from scripts.setup import is_valid_discord_token, is_valid_discord_id


def test_is_valid_discord_token_basic():
    assert is_valid_discord_token('Bot abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-') in (True, False)
    assert is_valid_discord_token('mfa.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx') in (True, False)
    assert is_valid_discord_token('invalid') is False


def test_is_valid_discord_id():
    assert is_valid_discord_id('12345678901234567') is True
    assert is_valid_discord_id('abc') is False