import json
import os
from typing import Dict, Any
from util.logger import logger

class CommandLoader:
    """
    Utility class to load command configurations from JSON files.
    """
    
    @staticmethod
    def load_commands(platform: str, command_file: str) -> Dict[str, Any]:
        """
        Loads commands from a JSON file based on the platform and filename.
        
        Args:
            platform (str): The platform name (e.g., 'athena', 'argo').
            command_file (str): The name of the command file without extension (e.g., 'system_info').
            
        Returns:
            Dict[str, Any]: A dictionary containing the loaded commands. Returns empty dict on failure.
        """
        # Construct the file path
        # Assuming resources is at the root level, relative to the execution path or known location
        # Adjust base path logic as needed. Here we assume running from project root.
        base_path = os.path.join(os.getcwd(), "resources", "commands")
        file_path = os.path.join(base_path, platform.lower(), f"{command_file}.json")
        
        if not os.path.exists(file_path):
            logger.error(f"Command file not found: {file_path}")
            return {}
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading command file {file_path}: {e}")
            return {}
