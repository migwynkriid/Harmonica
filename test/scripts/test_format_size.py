from scripts.format_size import format_size


def test_format_size_units():
    assert format_size(512) == "512.00 B"
    assert format_size(1024) == "1.00 KB"
    assert format_size(1024 * 1024) == "1.00 MB"
    assert format_size(1024 * 1024 * 2.5).startswith("2.50 MB")