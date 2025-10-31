import importlib
import pytest


@pytest.mark.asyncio
async def test_queue_setup_registers(bot):
    mod = importlib.import_module('commands.queue')
    setup = getattr(mod, 'setup', None)
    initial_cogs = set(bot.cogs.keys())
    initial_cmds = set(cmd.qualified_name for cmd in bot.walk_commands())
    if setup:
        await setup(bot)
    new_cogs = set(bot.cogs.keys())
    new_cmds = set(cmd.qualified_name for cmd in bot.walk_commands())
    assert new_cogs != initial_cogs or new_cmds != initial_cmds