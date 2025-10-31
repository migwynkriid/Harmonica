def test_constants_values():
    import scripts.constants as c
    assert isinstance(c.RED, str) and '\033[' in c.RED
    assert isinstance(c.GREEN, str) and '\033[' in c.GREEN
    assert isinstance(c.BLUE, str) and '\033[' in c.BLUE
    assert isinstance(c.YELLOW, str) and '\033[' in c.YELLOW
    assert isinstance(c.RESET, str) and '\033[' in c.RESET