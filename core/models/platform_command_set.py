#!/usr/bin/env python
"""
Platform Command Set Module
Manage command sets for different platforms
"""
from typing import Dict, List, Any, Optional
import json
import os
import sys
import platform
from enum import Enum
from util.logger import logger


class CommandType(Enum):
    """Command type enumeration"""
    SYSTEM_INFO = "system_info"
    AUTO_DIAGNOSTIC = "auto_diagnostic"
    FUNCTIONALITY = "functionality"
    CONFIGURATION = "configuration"


class PlatformCommandSet:
    """
    Platform Command Set Management Class
    Load, manage, and retrieve command sets for different platforms
    """
    
    def __init__(self, commands_dir: str = None, platform_name: str = "hydra"):
        """
        Initialize the platform command set
        
        Args:
            commands_dir: The directory of command set configuration files, default is resources/commands
            platform_name: The name of the platform, i.e. the project name, used to load the corresponding command set
        """
        # Default command set directory
        if commands_dir is None:
            # Determine the base path
            if hasattr(sys, '_MEIPASS'):
                # Temporary folder created by PyInstaller
                base_path = sys._MEIPASS
            else:
                # Normal development environment
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            self.commands_dir = os.path.join(base_path, "resources", "commands")
        else:
            self.commands_dir = commands_dir
            
        # Command set cache
        self.command_sets: Dict[CommandType, Dict[str, str]] = {}
        
        # Set the current platform (project) name
        self.platform_name = platform_name
        
        # Load the command set
        self._load_command_sets()
    
    def set_platform(self, platform_name: str):
        """
        Set the platform (project) name and reload the command set
        
        Args:
            platform_name: The name of the platform
        """
        self.platform_name = platform_name
        logger.info(f"Set platform: {self.platform_name}")
        self._load_command_sets()
        
    def _load_command_sets(self):
        """Load all command sets"""
        # Clear existing command sets
        self.command_sets = {}
        
        # Determine the platform directory path
        platform_dir = os.path.join(self.commands_dir, self.platform_name)
        common_dir = os.path.join(self.commands_dir, "common")
        
        # Initialize the command type dictionary
        for cmd_type in CommandType:
            self.command_sets[cmd_type] = {}
        
        # Load the common command set (if it exists)
        if os.path.exists(common_dir):
            self._load_commands_from_dir(common_dir)
            
        # Load the platform specific command set (if it exists)
        if os.path.exists(platform_dir):
            self._load_commands_from_dir(platform_dir)
        else:
            logger.warning(f"Platform directory not found: {platform_dir}")
    
    def _load_commands_from_dir(self, dir_path: str):
        """
        Load command set files from a specified directory
        
        Args:
            dir_path: The directory path
        """
        for cmd_type in CommandType:
            # The command set file name format: {command type}.json
            # For example: system_info.json, auto_diagnostic.json
            file_name = f"{cmd_type.value}.json"
            file_path = os.path.join(dir_path, file_name)
            
            # If the file exists, load the command set
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        commands = json.load(f)
                        # Update the command set, platform specific commands will override the common commands
                        self.command_sets[cmd_type].update(commands)
                except Exception as e:
                    print(f"Failed to load command set: {file_path}, error: {str(e)}")
    
    def get_command(self, command_type: CommandType, command_name: str) -> Optional[Any]:
        """
        Get the command of a specified type and name
        
        Args:
            command_type: The command type
            command_name: The command name
            
        Returns:
            The command data (string, list, or dict), return None if not found
        """
        if command_type in self.command_sets and command_name in self.command_sets[command_type]:
            cmd_data = self.command_sets[command_type][command_name]
            
            # Handle new object format with "commands" key
            if isinstance(cmd_data, dict) and "commands" in cmd_data:
                return cmd_data["commands"]
            
            # Handle legacy format (direct list or string)
            return cmd_data
            
        return None
    
    def get_command_metadata(self, command_type: CommandType, command_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the complete command metadata (for new object format)
        
        Args:
            command_type: The command type
            command_name: The command name
            
        Returns:
            The complete command metadata dict, or None if not found
        """
        if command_type in self.command_sets and command_name in self.command_sets[command_type]:
            cmd_data = self.command_sets[command_type][command_name]
            
            # If it's the new object format, return as is
            if isinstance(cmd_data, dict):
                return cmd_data
            
            # If it's legacy format, wrap it
            if isinstance(cmd_data, list):
                return {"commands": cmd_data}
            elif isinstance(cmd_data, str):
                return {"commands": [cmd_data]}
                
        logger.warning(f"Command not found: {command_type} {command_name}")
        return None
    
    def get_all_commands(self, command_type: CommandType) -> Dict[str, str]:
        """
        Get all commands of a specified type
        
        Args:
            command_type: The command type
            
        Returns:
            The command dictionary {command name: command string}
        """
        if command_type in self.command_sets:
            return self.command_sets[command_type]
        logger.warning(f"Command type not found: {command_type}")
        return {}
    
    def save_command_set(self, command_type: CommandType, commands: Dict[str, str], is_common: bool = False):
        """
        Save the command set to a file
        
        Args:
            command_type: The command type
            commands: The command dictionary {command name: command string}
            is_common: Whether the command is common, True to save to the common directory, False to save to the platform specific directory
        """
        # Determine the save directory
        if is_common:
            target_dir = os.path.join(self.commands_dir, "common")
        else:
            target_dir = os.path.join(self.commands_dir, self.platform_name)
        
        # Ensure the directory exists
        os.makedirs(target_dir, exist_ok=True)
        
        # Save to a file
        file_name = f"{command_type.value}.json"
        file_path = os.path.join(target_dir, file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(commands, f, ensure_ascii=False, indent=2)
            
            # Update the command set in memory
            if command_type not in self.command_sets:
                self.command_sets[command_type] = {}
            
            self.command_sets[command_type].update(commands)
            
            return True
        except Exception as e:
            print(f"Failed to save command set: {file_path}, error: {str(e)}")
            return False
    
    def get_available_platforms(self) -> List[str]:
        """
        Get the list of available platforms (projects)
        
        Returns:
            The list of available platforms (projects)
        """
        platforms = []
        
        # Scan all subdirectories in the commands directory
        try:
            for item in os.listdir(self.commands_dir):
                item_path = os.path.join(self.commands_dir, item)
                if os.path.isdir(item_path) and item != "common":
                    platforms.append(item)
        except Exception as e:
            print(f"Failed to get available platforms: {e}")
            
        return platforms 