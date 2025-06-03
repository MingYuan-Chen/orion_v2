"""
System information service module
Provide system information update functionality for dashboard
"""
from PySide6.QtCore import QObject, Signal, Slot, QTimer, QThread
import json
from typing import Dict, Any, Optional, List
from util.logger import logger
from core.models.platform_command_set import PlatformCommandSet, CommandType

class SystemInfoService(QObject):
    """
    System information service
    Provides functionality to get and refresh system information
    """
    # Define signals
    info_received = Signal(str, dict)  # device_id, system_info
    info_error = Signal(str, str)      # device_id, error_message
    command_executed = Signal(str, str, str)  # device_id, command_name, command
    
    def __init__(self, serial_worker, platform_name="hydra_fhd"):
        """
        Initialize system info service
        
        Args:
            serial_worker: Serial device worker for command execution
            platform_name: Platform name for command set, default is "hydra_fhd"
        """
        super().__init__()
        self.serial_worker = serial_worker
        
        # Initialize platform command set
        self.platform_command_set = PlatformCommandSet(platform_name=platform_name)
        # Get system info commands
        self.commands = self._get_commands_from_platform()
        
        self.pending_commands = []
        self.current_device_id = None
        self.collected_info = {}
        # Add update flag
        self.is_updating = False
        
        # Connect command result signal
        self.serial_worker.command_result.connect(self._on_command_completed)

        # LED status map
        self.LED_STATUS_MAP = {
            1: ("Blue", "blue"), 9: ("Blue Blinking", "blue"),
            2: ("Green", "green"), 10: ("Green Blinking", "green"),
            3: ("Cyan", "cyan"), 11: ("Cyan Blinking", "cyan"),
            4: ("Red", "red"), 12: ("Red Blinking", "red"),
            5: ("Fuchsia", "fuchsia"), 13: ("Fuchsia Blinking", "fuchsia"),
            6: ("Orange", "orange"), 14: ("Orange Blinking", "orange"),
            7: ("White", "white"), 15: ("White Blinking", "white")
        }
    
    def _get_commands_from_platform(self):
        """
        Get commands from platform command set
        
        Returns:
            Dictionary of command names to command strings
        """
        # Get all system info commands from platform command set
        system_info_commands = self.platform_command_set.get_all_commands(CommandType.SYSTEM_INFO)
        
        # Convert command format: some commands may be lists of strings in JSON
        command_dict = {}
        for cmd_name, cmd_value in system_info_commands.items():
            if isinstance(cmd_value, list) and len(cmd_value) > 0:
                # Use the first command in the list
                command_dict[cmd_name] = cmd_value[0]
            else:
                command_dict[cmd_name] = cmd_value
                
        logger.info(f"Loaded {len(command_dict)} system info commands from platform command set")
        return command_dict
    
    def set_platform(self, platform_name: str):
        """
        Set platform name and reload commands
        
        Args:
            platform_name: Platform name
        """
        logger.info(f"Setting platform to: {platform_name}")
        self.platform_command_set.set_platform(platform_name)
        self.commands = self._get_commands_from_platform()
    
    def get_commands(self):
        """
        Get commands for fetching system information (For compatibility)
        """
        return self.commands
    
    def update_system_info(self, device_id: str):
        """
        Start fetching system information for specified device
        
        Args:
            device_id: Target device ID
        """
        # If already fetching info, return
        if self.pending_commands:
            logger.warning(f"System info update already in progress for device: {self.current_device_id}")
            return False
        
        logger.info(f"Starting system info update for device: {device_id}")
        self.current_device_id = device_id
        self.collected_info = {}
        
        # Set update flag to True
        self.is_updating = True
        
        # Copy command list to execute sequentially
        self.pending_commands = list(self.commands.items())
        
        # Start executing the first command
        self._execute_next_command()
        
        return True
    
    def _execute_next_command(self):
        """
        Execute the next command in the queue
        """
        if not self.pending_commands or not self.current_device_id:
            # All commands have been executed
            if self.collected_info:
                logger.info(f"System info collection completed for device: {self.current_device_id}")
                self.info_received.emit(self.current_device_id, self.collected_info)
            
            # Reset update flag
            self.is_updating = False
            return
        
        # Get the next command to execute
        command_name, command = self.pending_commands.pop(0)
        
        # Emit command executed signal before executing command
        self.command_executed.emit(self.current_device_id, command_name, command)
        logger.debug(f"Executing system info command: [{self.current_device_id}] {command_name} - {command}")
        
        # Execute command and receive result in signal processing
        try:
            # Use different timeouts based on command type
            if command_name in ["uboot_version", "pic_firmware"] or "i2ctransfer" in command:
                # Complex commands need more time
                timeout = 8
            elif command_name in ["os_version", "cpu_info", "memory_info"]:
                # Simple commands can use shorter timeout
                timeout = 5
            else:
                timeout = 6
                
            self.serial_worker.send_command(self.current_device_id, command, timeout)
        except Exception as e:
            logger.error(f"Error sending command {command_name}: {str(e)}")
            self._execute_next_command()
    
    @Slot(str, str, str)
    def _on_command_completed(self, device_id: str, command: str, response: str):
        """
        Handle command completion
        
        Args:
            device_id: Device ID
            command: Executed command
            response: Command response
        """
        # If not active update status, skip processing to avoid triggering system info update
        if not self.is_updating:
            return
            
        # Ensure it's the device and command we care about
        if device_id != self.current_device_id:
            return
        
        # Find command name
        command_name = None
        for name, cmd in self.commands.items():
            if cmd in command:
                command_name = name
                break
        
        if not command_name:
            logger.warning(f"Received response for unknown command: {command}")
            # Only continue to execute when actively updating and there are pending commands
            if self.is_updating and self.pending_commands:
                self._execute_next_command()
            return
        
        # Record response (仅在调试级别记录，避免产生大量日志)
        logger.debug(f"Received response for {command_name}")
        logger.debug(f"Response: {response}")
        
        # Process response
        try:
            # Parse response and store in collected info
            if command_name == "cpu_info":
                self.collected_info["cpu"] = self._parse_cpu_info(response)
            elif command_name == "memory_info":
                self.collected_info["memory"] = self._parse_memory_info(response)
            elif command_name == "disk_usage":
                self.collected_info["storage"] = self._parse_disk_info(response)
            elif command_name in ["capacity", "full_capacity", "relative_state", "charging_voltage", 
                                 "charging_current", "temperature", "cycle_count", "led_status", "dc_status"]:
                # Use battery info parsing function to handle battery related commands
                if "battery" not in self.collected_info:
                    self.collected_info["battery"] = {}
                
                # Parse and store battery data
                parsed_value = self._parse_battery_info(command_name, response)
                if parsed_value is not None:
                    self.collected_info["battery"][command_name] = parsed_value
            elif command_name in ["uboot_version", "pic_firmware", "os_version"]:
                # Handle firmware and OS information commands
                if "firmware_os" not in self.collected_info:
                    self.collected_info["firmware_os"] = {}
                
                # Parse and store firmware/OS data
                parsed_value = self._parse_firmware_os_info(command_name, response)
                self.collected_info["firmware_os"][command_name] = parsed_value
            else:
                # Store original response
                self.collected_info[command_name] = response
        except Exception as e:
            logger.error(f"Error parsing response for {command_name}: {str(e)}")
        
        # Add delay before next command, especially for i2c commands
        if command_name and ("i2ctransfer" in self.commands.get(command_name, "") or 
                           command_name in ["pic_firmware", "relative_state", "charging_voltage", "charging_current", "temperature"]):
            # Add extra delay for i2c commands to prevent response mixing
            # Use longer delay for relative_state as it's particularly problematic
            delay = 1500 if command_name == "relative_state" else 800
            QTimer.singleShot(delay, self._execute_next_command)
        else:
            # Execute next command immediately for non-i2c commands
            self._execute_next_command()
    
    def _parse_cpu_info(self, response: str) -> Dict[str, Any]:
        """
        Parse CPU information from command response
        
        Args:
            response: Command response
            
        Returns:
            Parsed CPU information
        """
        cpu_info = {}
        
        try:
            # Split response into lines and look for the actual hardware information
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            
            # Look for lines that contain hardware information (not command echoes)
            for line in lines:
                # Skip command echo lines
                if 'grep' in line or 'Hardware' in line and 'proc' in line:
                    continue
                # Skip prompt lines
                if 'root@' in line or line.startswith('#'):
                    continue
                # Look for hardware model information
                if any(keyword in line.lower() for keyword in ['freescale', 'imx', 'mx6', 'cortex', 'arm', 'intel', 'amd']):
                    cpu_info["model"] = line.strip()
                    break
            
            # If no specific hardware model found, try to find any non-empty line that's not a command
            if "model" not in cpu_info:
                for line in lines:
                    if (line and 
                        'grep' not in line and 
                        'Hardware' not in line and 
                        'proc' not in line and
                        'root@' not in line and 
                        not line.startswith('#') and
                        len(line) > 3):  # Ensure it's meaningful content
                        cpu_info["model"] = line.strip()
                        break
            
            # Final fallback
            if "model" not in cpu_info:
                cpu_info["model"] = "Unknown"
                
        except Exception as e:
            logger.warning(f"Failed to parse CPU information: {response} - Error: {e}")
            cpu_info["model"] = "Unknown"
        
        return cpu_info
    
    def _parse_memory_info(self, response: str) -> Dict[str, Any]:
        """
        Parse memory information from free command with grep 'Mem:'
        
        Args:
            response: Command response
            
        Returns:
            Parsed memory information
        """
        memory_info = {}
        
        lines = response.strip().split('\n')
        for line in lines:
            if 'Mem:' in line:
                parts = line.split()
                # For response: "Mem:           3.7G        272M        3.2G        496K        251M        3.3G"
                # parts[0] = "Mem:", parts[1] = "3.7G", parts[2] = "272M", etc.
                if len(parts) >= 7:  # Ensure there is enough data
                    try:
                        memory_info["total"] = parts[1]     # Total memory
                        memory_info["used"] = parts[2]      # Used
                        memory_info["free"] = parts[3]      # Available
                        memory_info["shared"] = parts[4]    # Shared
                        memory_info["buffers"] = parts[5]   # Buffers
                        memory_info["available"] = parts[6]  # Available
                        
                        # Calculate usage rate (optional)
                        try:
                            # Convert '3.7G' to number (remove G)
                            total = float(parts[1].replace('G', '').replace('M', 'e-3').replace('K', 'e-6'))
                            used = float(parts[2].replace('G', '').replace('M', 'e-3').replace('K', 'e-6'))
                            memory_info["usage_percent"] = round((used / total) * 100, 1)
                        except:
                            pass  # If calculation fails, skip
                    except Exception as e:
                        logger.warning(f"Failed to parse memory information: {e}")
                break  # Only process the first line containing Mem: data
        
        logger.debug(f"Parsed memory info: {memory_info}")
        return memory_info
    
    def _parse_disk_info(self, response: str) -> Dict[str, str]:
        """Parse disk information from response.
        
        Args:
            response: Response from df command
            
        Returns:
            Dict containing disk information
        """
        disk_info = {}
        
        try:
            # 只取第一行数字
            total_sectors = int(response.strip().split('\n')[0])
            # 转换为字节 (512 bytes per sector)
            total_bytes = total_sectors * 512
            # 转换为 GB
            total_gb = total_bytes / (1024 ** 3)
            
            disk_info["total"] = f"128G"
            disk_info["available"] = f"{total_gb:.2f}G"
            disk_info["type"] = "eMMC"  # 默认假设为 eMMC
            
            logger.debug(f"Parsed disk info: {disk_info}")
            return disk_info
            
        except Exception as e:
            logger.warning(f"Failed to parse disk information: {e}")
            return disk_info
    
    def _parse_battery_info(self, command_name: str, response: str) -> Any:
        """
        Parse battery information from i2ctransfer commands
        
        Args:
            command_name: Name of the command (capacity, full_capacity, etc.)
            response: Command response
            
        Returns:
            Parsed battery information value
        """
        try:
            value = response
            
            # Special processing for dc_status
            if command_name == "dc_status":
                try:
                    value = int(response.strip().split("\n")[0])
                    logger.debug(f"Parsed {command_name}: {value}")
                    return value
                except Exception as e:
                    logger.error(f"Failed to parse {command_name}: {e}")
                    return None
            
            # Process i2ctransfer command results
            if command_name in ["capacity", "full_capacity", "relative_state", "charging_voltage", 
                               "charging_current", "temperature", "cycle_count", "led_status"]:
                try:
                    # Enhanced parsing for i2c responses with better error handling
                    # Look for hex values more robustly
                    lines = response.strip().split('\n')
                    hex_values = []
                    command_hex_values = {}  # Track hex values by command type
                    
                    current_command_context = None
                    for line in lines:
                        # Skip command echo lines
                        if 'i2ctransfer' in line or 'sleep' in line or 'root@' in line:
                            # Detect which command this line belongs to based on register address
                            if command_name == "relative_state" and "0x0d" in line:
                                current_command_context = "relative_state"
                            elif command_name == "charging_voltage" and "0x15" in line:
                                current_command_context = "charging_voltage"
                            elif command_name == "charging_current" and "0x14" in line:
                                current_command_context = "charging_current"
                            elif command_name == "temperature" and "0x08" in line:
                                current_command_context = "temperature"
                            elif command_name == "pic_firmware" and "0x10" in line:
                                current_command_context = "pic_firmware"
                            continue
                            
                        # Look for hex values in the line
                        if '0x' in line:
                            line_hex = [x.strip() for x in line.split() if x.startswith('0x')]
                            if line_hex:
                                hex_values.extend(line_hex)
                                # Associate hex values with current command context
                                if current_command_context:
                                    if current_command_context not in command_hex_values:
                                        command_hex_values[current_command_context] = []
                                    command_hex_values[current_command_context].extend(line_hex)
                    
                    # Try to use command-specific hex values first
                    target_hex_values = command_hex_values.get(command_name, hex_values)
                    
                    # Special handling for pic_firmware
                    if command_name == "pic_firmware":
                        if len(target_hex_values) >= 3:
                            # Response structure: [status_byte, version_high, version_low]
                            # Skip the first hex value (0x00 status byte) and use the next two
                            version_high = target_hex_values[1]  # "0x01"
                            version_low = target_hex_values[2]   # "0x02"
                            # Combine as "0x0102" then convert to int
                            combined_hex = "0x" + version_high[2:] + version_low[2:]  # "0x0102"
                            firmware_version = int(combined_hex, 16)  # 258
                            return f"v{firmware_version}"
                        elif len(target_hex_values) == 2:
                            # If only two values, assume they are version data
                            version_high = target_hex_values[0]  # "0x01"
                            version_low = target_hex_values[1]   # "0x02"
                            # Combine as "0x0102" then convert to int
                            combined_hex = "0x" + version_high[2:] + version_low[2:]  # "0x0102"
                            firmware_version = int(combined_hex, 16)  # 258
                            return f"v{firmware_version}"
                        else:
                            value = int(target_hex_values[0], 16) if target_hex_values else 0
                            logger.debug(f"Parsed {command_name}: {value} (from hex values: {target_hex_values})")
                            return value
                    else:
                        # Extract the correct hex values based on expected pattern
                        if len(target_hex_values) >= 2:
                            # For multi-byte values, take the last two meaningful hex values
                            # Filter out status bytes (0x02) which are common in responses
                            data_hex = [h for h in target_hex_values if h != '0x02']
                            
                            if len(data_hex) >= 2:
                                high_byte = int(data_hex[-2], 16)
                                low_byte = int(data_hex[-1], 16)
                                value = (high_byte << 8) + low_byte
                            elif len(data_hex) == 1:
                                value = int(data_hex[0], 16)
                            else:
                                # Fall back to using all hex values if no data hex found
                                if len(target_hex_values) >= 2:
                                    high_byte = int(target_hex_values[-2], 16)
                                    low_byte = int(target_hex_values[-1], 16)
                                    value = (high_byte << 8) + low_byte
                                else:
                                    value = int(target_hex_values[-1], 16)
                        elif len(target_hex_values) == 1:
                            value = int(target_hex_values[0], 16)
                        else:
                            # Fallback to original parsing method
                            if "r2" in response:
                                value_part = response.split("r2")[1].split("root")[0]
                                value_line = [line for line in value_part.split('\n') if '0x' in line]
                                if value_line:
                                    value = int(value_line[0].replace(' 0x', '').replace('0x', ''), 16)
                                else:
                                    raise ValueError("No hex values found in response")
                            else:
                                raise ValueError("Invalid response format")
                        
                        # Convert format according to different types
                        if command_name == "capacity":
                            # Return capacity value directly
                            parsed_value = value
                        elif command_name == "full_capacity":
                            # Return full capacity value directly
                            parsed_value = value
                        elif command_name == "relative_state":
                            # Return relative state value directly
                            parsed_value = value
                        elif command_name == "charging_voltage":
                            # Convert voltage to volts (V)
                            parsed_value = round(float(value/1000), 2)
                        elif command_name == "charging_current":
                            # Convert current to amperes (A)
                            parsed_value = round(float(value/1000), 2)
                        elif command_name == "temperature":
                            # Convert temperature to Celsius (°C)
                            parsed_value = round(float(value/10)-273.15, 2)
                        elif command_name == "cycle_count":
                            # Return cycle count value directly
                            parsed_value = value
                        elif command_name == "led_status":
                            # Return LED status value directly
                            parsed_value = value
                        else:
                            parsed_value = value
                        
                        logger.debug(f"Parsed {command_name}: {parsed_value} (from hex values: {target_hex_values})")
                        return parsed_value
                    
                except Exception as e:
                    logger.error(f"Failed to parse {command_name}: {e}")
                    return None
            
            # If it's not a known battery command, return the original response
            return response
            
        except Exception as e:
            logger.error(f"Error in battery info parsing for {command_name}: {str(e)}")
            return None
    
    def cleanup(self):
        """
        Clean up resources
        """
        # Disconnect signal
        try:
            self.serial_worker.command_result.disconnect(self._on_command_completed)
        except Exception:
            pass
        
        # Clear status
        self.pending_commands = []
        self.current_device_id = None
        self.collected_info = {}
        self.is_updating = False
        
        logger.info("System info service cleaned up")
    
    def _parse_firmware_os_info(self, command_name: str, response: str) -> str:
        """
        Parse firmware and OS information from command response
        
        Args:
            command_name: Command name (uboot_version, pic_firmware, os_version)
            response: Command response
            
        Returns:
            Parsed information string
        """
        try:
            # Clean up response first
            clean_response = response.strip()
            lines = [line.strip() for line in clean_response.split('\n') if line.strip()]
            
            if command_name == "uboot_version":
                # Parse U-Boot version from strings output
                for line in lines:
                    if 'U-Boot' in line and any(char.isdigit() for char in line):
                        # Extract version information
                        return line.strip()
                return "Unknown U-Boot Version"
                
            elif command_name == "pic_firmware":
                # Parse PIC firmware version from i2c response
                try:
                    # Enhanced parsing for PIC firmware
                    lines = response.strip().split('\n')
                    hex_values = []
                    
                    for line in lines:
                        # Skip command echo lines
                        if 'i2ctransfer' in line or 'sleep' in line or 'root@' in line:
                            continue
                        # Look for hex values in the line
                        if '0x' in line:
                            line_hex = [x.strip() for x in line.split() if x.startswith('0x')]
                            hex_values.extend(line_hex)
                    
                    if len(hex_values) >= 3:
                        # Response structure: [status_byte, version_high, version_low]
                        # Skip the first hex value (0x00 status byte) and use the next two
                        version_high = hex_values[1]  # "0x01"
                        version_low = hex_values[2]   # "0x02"
                        # Combine as "0x0102" then convert to int
                        combined_hex = "0x" + version_high[2:] + version_low[2:]  # "0x0102"
                        firmware_version = int(combined_hex, 16)  # 258
                        return f"v{firmware_version}"
                    elif len(hex_values) == 2:
                        # If only two values, assume they are version data
                        version_high = hex_values[0]  # "0x01"
                        version_low = hex_values[1]   # "0x02"
                        # Combine as "0x0102" then convert to int
                        combined_hex = "0x" + version_high[2:] + version_low[2:]  # "0x0102"
                        firmware_version = int(combined_hex, 16)  # 258
                        return f"v{firmware_version}"
                    elif len(hex_values) == 1:
                        # Single hex value
                        firmware_version = int(hex_values[0], 16)
                        return f"v{firmware_version}"
                    else:
                        # Fallback to original parsing
                        if "r2" in response:
                            value_part = response.split("r2")[1].split("root")[0]
                            value_line = [line for line in value_part.split('\n') if '0x' in line]
                            if value_line:
                                hex_val = value_line[0].replace(' 0x', '').replace('0x', '')
                                firmware_version = int(hex_val, 16)
                                return f"v{firmware_version}"
                        raise ValueError("No valid firmware version found")
                except Exception as e:
                    logger.debug(f"Error parsing PIC firmware: {e}")
                    
                return "Unknown PIC Version"
                
            elif command_name == "os_version":
                # Parse OS version from uname -a output
                for line in lines:
                    if 'Linux' in line and any(char.isdigit() for char in line):
                        # Extract kernel information, avoid command echoes
                        if not line.startswith('uname'):
                            # Clean up the line by splitting at first # and taking the part before
                            clean_line = line.split('#')[0].strip()
                            return clean_line if clean_line else line.strip()
                return "Unknown OS Version"
                
            else:
                # Return original response for unknown commands
                return clean_response[:100] if clean_response else "No response"
                
        except Exception as e:
            logger.warning(f"Failed to parse {command_name}: {e}")
            return clean_response[:100] if clean_response else "Parse error"


if __name__ == "__main__":
    """Test system info service"""
    from core.workers.serial_device_worker import SerialDeviceWorker
    from core.models.device_manager_model import DeviceManagerModel
    from PySide6.QtWidgets import QApplication
    import sys
    def main():
        # Create application
        app = QApplication(sys.argv)
        device_manager = DeviceManagerModel()
        serial_device_worker = SerialDeviceWorker(device_manager)
        serial_device_worker.connect_device("device1", "COM4", 115200, 10)
        system_info_service = SystemInfoService(serial_device_worker)
        
        def on_system_info_received(device_id, info):
            logger.info(f"System info received for device: {device_id}")
            logger.info(f"System info: {info}")
            QTimer.singleShot(1000, lambda: system_info_service.cleanup())
            QTimer.singleShot(5000, lambda: QApplication.quit())
            
        def on_system_info_error(device_id, error):
            logger.error(f"Error fetching system info for device: {device_id}")
            logger.error(f"Error: {error}")
        
        # Connect signals
        system_info_service.info_received.connect(on_system_info_received)
        system_info_service.info_error.connect(on_system_info_error)
        
        # Test system info service
        system_info_service.update_system_info("device1")
        
        sys.exit(app.exec())

    sys.exit(main())


