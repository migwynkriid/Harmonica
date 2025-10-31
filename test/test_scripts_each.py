import os
import importlib
import pytest


def list_script_modules():
    for filename in os.listdir('scripts'):
        if filename.endswith('.py') and not filename.startswith('_'):
            yield f"scripts.{filename[:-3]}"


@pytest.mark.parametrize('modname', list(list_script_modules()))
def test_each_script_imports(modname):
    # Import script module to ensure it loads without raising exceptions
    module = importlib.import_module(modname)
    assert module is not None