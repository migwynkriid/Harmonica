import pytest


@pytest.mark.asyncio
async def test_handle_connection_error_dns(monkeypatch):
    from scripts.connection_handler import ConnectionHandler
    import scripts.connection_handler as ch
    # Speed up by removing sleeps
    async def fast_sleep(s):
        return None
    monkeypatch.setattr(ch.asyncio, 'sleep', fast_sleep)
    class DummyBot: pass
    # Force DNS check to succeed
    async def ok():
        return True
    monkeypatch.setattr(ConnectionHandler, 'check_dns_resolution', ok)
    import socket
    err = socket.gaierror(11004, 'dns error')
    handled = await ConnectionHandler.handle_connection_error(err, DummyBot())
    assert handled is True


@pytest.mark.asyncio
async def test_handle_connection_error_client(monkeypatch):
    from scripts.connection_handler import ConnectionHandler
    import scripts.connection_handler as ch
    # Speed up by removing sleeps
    async def fast_sleep(s):
        return None
    monkeypatch.setattr(ch.asyncio, 'sleep', fast_sleep)
    from aiohttp import ClientConnectorError
    import types
    conn_key = types.SimpleNamespace(host='discord.com', port=443, ssl=False)
    err = ClientConnectorError(conn_key, OSError('test'))
    handled = await ConnectionHandler.handle_connection_error(err, object())
    assert handled is True