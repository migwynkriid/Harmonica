import pytest
import types

from scripts.permissions import check_dj_role, check_admin_role


@pytest.mark.asyncio
async def test_check_dj_role_allows_when_config_disabled(monkeypatch, stub_ctx):
    # Simulate config where REQUIRES_DJ_ROLE is False
    fake_config = {'PERMISSIONS': {'REQUIRES_DJ_ROLE': False}}
    import scripts.permissions as perms
    monkeypatch.setattr(perms, 'load_config', lambda: fake_config)

    called = {'ok': False}

    class C:
        @check_dj_role()
        async def fn(self, ctx):
            called['ok'] = True

    await C().fn(stub_ctx)
    assert called['ok'] is True


@pytest.mark.asyncio
async def test_check_dj_role_requires_role(monkeypatch, stub_ctx):
    # Simulate config where REQUIRES_DJ_ROLE is True
    fake_config = {'PERMISSIONS': {'REQUIRES_DJ_ROLE': True}}
    import scripts.permissions as perms
    monkeypatch.setattr(perms, 'load_config', lambda: fake_config)

    # User without DJ role should not call fn
    called = {'ok': False}

    class C:
        @check_dj_role()
        async def fn(self, ctx):
            called['ok'] = True

    await C().fn(stub_ctx)
    assert called['ok'] is False

    # Grant DJ role using exact guild role instance
    dj_role = next((r for r in stub_ctx.guild.roles if getattr(r, 'name', '') == 'DJ'), None)
    stub_ctx.author.roles.append(dj_role)
    await C().fn(stub_ctx)
    assert called['ok'] is True


@pytest.mark.asyncio
async def test_check_admin_role_requires_role(monkeypatch, stub_ctx):
    # Enable admin requirement
    fake_config = {'PERMISSIONS': {'REQUIRES_ADMIN_ROLE': True}}
    import scripts.permissions as perms
    monkeypatch.setattr(perms, 'load_config', lambda: fake_config)

    called = {'ok': False}

    class C:
        @check_admin_role()
        async def fn(self, ctx):
            called['ok'] = True

    # Without Administrator role
    await C().fn(stub_ctx)
    assert called['ok'] is False

    # Grant Administrator role using exact guild role instance
    admin_role = next((r for r in stub_ctx.guild.roles if getattr(r, 'name', '') == 'Administrator'), None)
    stub_ctx.author.roles.append(admin_role)
    await C().fn(stub_ctx)
    assert called['ok'] is True