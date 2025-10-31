import importlib
import pytest


@pytest.mark.asyncio
async def test_alias_management_servers_registers(bot):
    # servers
    mod = importlib.import_module('commands.servers')
    setup = getattr(mod, 'setup', None)
    if setup:
        await setup(bot)
    assert bot.walk_commands()