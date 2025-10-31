import os
import importlib
import pytest


@pytest.mark.asyncio
async def test_load_all_command_extensions(bot):
    """Load all commands via the extension loader and assert changes."""
    initial_cogs = set(bot.cogs.keys())
    initial_cmds = set(cmd.qualified_name for cmd in bot.walk_commands())

    # Load using our loader
    from scripts.load_commands import load_commands
    await load_commands(bot)

    new_cogs = set(bot.cogs.keys())
    new_cmds = set(cmd.qualified_name for cmd in bot.walk_commands())

    assert new_cogs != initial_cogs or new_cmds != initial_cmds, "No commands or cogs were loaded"


@pytest.mark.asyncio
async def test_setup_functions_register(bot):
    """Directly import each command module and call setup(bot) if present."""
    initial_cogs = set(bot.cogs.keys())
    initial_cmds = set(cmd.qualified_name for cmd in bot.walk_commands())

    for filename in os.listdir("commands"):
        if filename.endswith(".py") and not filename.startswith("_"):
            modname = f"commands.{filename[:-3]}"
            module = importlib.import_module(modname)
            setup = getattr(module, "setup", None)
            if setup:
                await setup(bot)

    new_cogs = set(bot.cogs.keys())
    new_cmds = set(cmd.qualified_name for cmd in bot.walk_commands())

    assert new_cogs != initial_cogs or new_cmds != initial_cmds, "Setup did not register any cogs/commands"