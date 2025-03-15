import asyncio
import socket
import logging
import time
from aiohttp import ClientConnectorError, ClientConnectorDNSError

logger = logging.getLogger(__name__)

class ConnectionHandler:
    """
    A utility class to handle connection issues with Discord's gateway.
    
    This class provides methods to handle common connection issues like DNS resolution
    failures, which can occur when a bot is disconnected for a longer period of time.
    """
    
    @staticmethod
    async def check_dns_resolution(hostname="discord.com", max_retries=5, retry_delay=5):
        """
        Check if DNS resolution is working properly.
        
        This method attempts to resolve a hostname using socket.getaddrinfo and
        retries if it fails, with an increasing delay between retries.
        
        Args:
            hostname (str): The hostname to resolve
            max_retries (int): Maximum number of retry attempts
            retry_delay (int): Initial delay between retries in seconds
            
        Returns:
            bool: True if DNS resolution is working, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Try to resolve the hostname
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: socket.getaddrinfo(hostname, 443)
                )
                return True
            except socket.gaierror as e:
                # DNS resolution failed
                logger.warning(f"DNS resolution failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # Wait before retrying with exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Waiting {wait_time} seconds before retrying...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"DNS resolution failed after {max_retries} attempts")
                    return False
    
    @staticmethod
    async def handle_connection_error(error, bot):
        """
        Handle connection errors that may occur during bot operation.
        
        This method provides specific handling for different types of connection errors,
        with special focus on DNS resolution failures.
        
        Args:
            error (Exception): The error that occurred
            bot (discord.Client): The bot instance
            
        Returns:
            bool: True if the error was handled, False otherwise
        """
        if isinstance(error, ClientConnectorDNSError) or (
            isinstance(error, socket.gaierror) and error.errno == 11004
        ):
            logger.error(f"DNS resolution error detected: {error}")
            logger.info("Checking DNS resolution...")
            
            # Check if DNS resolution is working
            dns_working = await ConnectionHandler.check_dns_resolution()
            
            if dns_working:
                logger.info("DNS resolution is now working, reconnection should succeed")
                return True
            else:
                logger.error("DNS resolution is still failing, reconnection may fail")
                # You could implement additional recovery steps here
                # For example, changing DNS servers or notifying the bot owner
                return False
        
        # Handle other types of connection errors
        elif isinstance(error, ClientConnectorError):
            logger.error(f"Connection error: {error}")
            # Wait a bit before reconnecting
            await asyncio.sleep(5)
            return True
        
        # Unknown error type
        return False

# Add a patch to discord.py's Client.connect method to handle DNS errors
def patch_discord_client():
    """
    Patch the discord.py Client.connect method to handle DNS resolution errors.
    
    This function monkey patches the discord.py library to add better handling
    for DNS resolution errors, which can occur when a bot is disconnected for
    a longer period of time.
    """
    import discord
    
    original_connect = discord.Client.connect
    
    async def patched_connect(self, *, reconnect=True):
        """
        Patched version of discord.Client.connect with better DNS error handling.
        """
        try:
            return await original_connect(self, reconnect=reconnect)
        except (ClientConnectorDNSError, socket.gaierror) as e:
            logger.error(f"DNS resolution error during connect: {e}")
            # Check DNS resolution and wait if needed
            dns_working = await ConnectionHandler.check_dns_resolution()
            if dns_working:
                logger.info("DNS resolution is now working, retrying connection...")
                return await original_connect(self, reconnect=reconnect)
            else:
                logger.error("DNS resolution is still failing, connection will likely fail")
                # Raise the original error
                raise
    
    # Apply the patch
    discord.Client.connect = patched_connect
    logger.info("Applied DNS resolution error handling patch to discord.Client.connect") 