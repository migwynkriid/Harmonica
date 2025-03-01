from datetime import datetime
import os
from scripts.constants import BLUE, GREEN, RESET

class CommandLogger:
    """
    Logger class for tracking command usage in the bot.
    
    This class provides functionality to log commands used in the bot,
    recording the username, command, server name, and timestamp.
    Logs are written to a file and also printed to the console.
    """
    
    def __init__(self):
        """
        Initialize the CommandLogger.
        
        Sets up the log file path based on the root directory of the bot.
        """
        self.log_file = "commandlog.txt"
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_path = os.path.join(self.root_dir, self.log_file)

    def log_command(self, username: str, command: str, server_name: str = "Unknown Server") -> None:
        """
        Log a command with username and timestamp to the command log file.
        
        This method writes a log entry to the command log file and also prints
        the command usage to the console with color formatting. The log entry
        includes the timestamp, username, command, and server name.
        
        Args:
            username (str): The username of the command sender
            command (str): The full command that was sent
            server_name (str): The name of the server where the command was used
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} - {username} has used command {command} in server: {server_name}\n"
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            
            # Append the log entry to the file
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            # Print to console in the requested format
            print(f"{BLUE}[{username}]{RESET} {GREEN}used the command:{RESET}{BLUE} {command}{RESET}{GREEN} in server: {RESET}{BLUE}{server_name}{RESET}")
        except Exception as e:
            print(f"Error logging command: {str(e)}")

# Create a singleton instance
command_logger = CommandLogger()
