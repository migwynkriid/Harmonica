from datetime import datetime
import os

class CommandLogger:
    def __init__(self):
        self.log_file = "commandlog.txt"
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_path = os.path.join(self.root_dir, self.log_file)

    def log_command(self, username: str, command: str) -> None:
        """
        Log a command with username and timestamp to the command log file.
        
        Args:
            username (str): The username of the command sender
            command (str): The full command that was sent
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} - {username} has used command {command}\n"
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            
            # Append the log entry to the file
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error logging command: {str(e)}")

# Create a singleton instance
command_logger = CommandLogger()
