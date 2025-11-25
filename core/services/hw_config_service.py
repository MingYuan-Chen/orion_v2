import json
import os
from typing import List, Dict, Optional
from util.logger import logger

class HWConfigService:
    """
    Service to handle loading and saving of hardware configuration JSON files.
    """
    def __init__(self):
        # Assuming resources is at the root level
        self.config_dir = os.path.join(os.getcwd(), "resources", "hw_config")
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except OSError as e:
                logger.error(f"Failed to create config directory: {e}")

    def get_config_files(self, platform_name: str) -> List[str]:
        """
        Returns a list of config filenames that match the given platform name.
        Matches if the filename starts with the platform name (case-insensitive).
        """
        if not platform_name or platform_name == "Unknown":
            return []
            
        matched_files = []
        try:
            if os.path.exists(self.config_dir):
                for filename in os.listdir(self.config_dir):
                    if filename.endswith(".json"):
                        # Check if filename starts with platform_name (case-insensitive)
                        # e.g. "athena" matches "athena_Small_..."
                        if filename.lower().startswith(platform_name.lower()):
                            matched_files.append(filename)
        except Exception as e:
            logger.error(f"Error listing config files: {e}")
            
        return sorted(matched_files)

    def load_config(self, filename: str) -> Dict:
        """
        Loads the content of a specific config file.
        """
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config file {filename}: {e}")
            return {}

    def save_config(self, filename: str, data: Dict) -> bool:
        """
        Saves the data to a config file.
        """
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config file {filename}: {e}")
            return False
