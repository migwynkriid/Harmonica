import asyncio
import socket
import logging
import time
import random
import sys
from aiohttp import ClientConnectorError, ClientConnectorDNSError

logger = logging.getLogger(__name__)

class ConnectionHandler:
    """
    A utility class to handle connection issues with Discord's gateway.
    
    This class provides methods to handle common connection issues like DNS resolution
    failures, which can occur when a bot is disconnected for a longer period of time.
    """
    
    # List of public DNS servers to try if the default DNS fails
    ALTERNATIVE_DNS = [
        "8.8.8.8",       # Google DNS
        "8.8.4.4",       # Google DNS (alternative)
        "1.1.1.1",       # Cloudflare DNS
        "1.0.0.1",       # Cloudflare DNS (alternative)
        "9.9.9.9",       # Quad9 DNS
        "149.112.112.112" # Quad9 DNS (alternative)
    ]
    
    # Track reconnection attempts
    reconnection_attempts = 0
    last_reconnection_time = 0
    
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
                logger.info(f"DNS resolution successful for {hostname}")
                return True
            except socket.gaierror as e:
                # DNS resolution failed
                logger.warning(f"DNS resolution failed (attempt {attempt+1}/{max_retries}): {e}")
                
                # If we've tried multiple times, try using an alternative DNS server
                if attempt >= 1:
                    # Try with an alternative DNS server
                    alt_dns = random.choice(ConnectionHandler.ALTERNATIVE_DNS)
                    logger.info(f"Trying alternative DNS server: {alt_dns}")
                    
                    # Create a custom resolver using the alternative DNS
                    try:
                        # This is a bit of a hack, but it can help in some cases
                        # We're manually setting the DNS server for this specific lookup
                        resolver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        resolver.connect((alt_dns, 53))
                        
                        # Try to resolve using this DNS server
                        query = b'\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07discord\x03com\x00\x00\x01\x00\x01'
                        resolver.send(query)
                        resolver.close()
                        
                        logger.info(f"Attempted alternative DNS resolution via {alt_dns}")
                    except Exception as dns_err:
                        logger.warning(f"Alternative DNS resolution failed: {dns_err}")
                
                if attempt < max_retries - 1:
                    # Wait before retrying with exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Waiting {wait_time} seconds before retrying DNS resolution...")
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
        # Track reconnection attempts
        current_time = time.time()
        if current_time - ConnectionHandler.last_reconnection_time > 300:  # Reset counter after 5 minutes
            ConnectionHandler.reconnection_attempts = 0
        
        ConnectionHandler.reconnection_attempts += 1
        ConnectionHandler.last_reconnection_time = current_time
        
        # If we've had too many reconnection attempts in a short time, wait longer
        if ConnectionHandler.reconnection_attempts > 5:
            wait_time = min(30, 5 * ConnectionHandler.reconnection_attempts)
            logger.warning(f"Multiple reconnection attempts detected. Waiting {wait_time} seconds before trying again...")
            await asyncio.sleep(wait_time)
        
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
                
                # Try to flush DNS cache on Windows
                try:
                    if sys.platform == 'win32':
                        logger.info("Attempting to flush DNS cache on Windows...")
                        import subprocess
                        subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
                        logger.info("DNS cache flush completed")
                except Exception as e:
                    logger.warning(f"Failed to flush DNS cache: {e}")
                
                # Wait a bit longer before reconnecting
                await asyncio.sleep(10)
                return True
        
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
    import sys
    
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
                
                # Try to flush DNS cache on Windows
                try:
                    if sys.platform == 'win32':
                        logger.info("Attempting to flush DNS cache on Windows...")
                        import subprocess
                        subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
                        logger.info("DNS cache flush completed")
                except Exception as e:
                    logger.warning(f"Failed to flush DNS cache: {e}")
                
                # Wait a bit before retrying
                await asyncio.sleep(5)
                
                # Try one more time
                try:
                    return await original_connect(self, reconnect=reconnect)
                except Exception as retry_error:
                    logger.error(f"Reconnection failed after DNS resolution check: {retry_error}")
                    # Raise the original error
                    raise
    
    # Apply the patch
    discord.Client.connect = patched_connect
    logger.info("Applied DNS resolution error handling patch to discord.Client.connect") 