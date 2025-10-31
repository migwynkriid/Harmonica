import os
import importlib
import pytest


def list_command_modules():
    for filename in os.listdir('commands'):
        if filename.endswith('.py') and not filename.startswith('_'):
            yield f"commands.{filename[:-3]}"


@pytest.mark.asyncio
@pytest.mark.parametrize('modname', list(list_command_modules()))
async def test_each_command_setup_registers(bot, modname):
    module = importlib.import_module(modname)
    setup = getattr(module, 'setup', None)

    initial_cogs = set(bot.cogs.keys())
    initial_cmds = set(cmd.qualified_name for cmd in bot.walk_commands())

    if setup:
        await setup(bot)

    new_cogs = set(bot.cogs.keys())
    new_cmds = set(cmd.qualified_name for cmd in bot.walk_commands())

    assert new_cogs != initial_cogs or new_cmds != initial_cmds, f"{modname} did not register any cog/command"