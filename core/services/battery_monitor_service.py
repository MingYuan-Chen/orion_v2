"""
Battery Monitor Service

Performance optimizations applied:
- Reduced command delay from 50ms to 20ms between commands
- Optimized command execution order (dc_status first for speed)  
- Removed non-essential DEBUG and INFO loggers from hot execution paths
- Retained critical WARNING and ERROR loggers for troubleshooting
"""
from PySide6.QtCore import QObject, Signal, Slot, QTimer
import json
import time
from typing import Dict, Any, Optional, List
import re
from util.logger import logger
from core.models.platform_command_set import PlatformCommandSet, CommandType

class BatteryMonitorService(QObject):
    """
    Battery Monitor Service
    Specialized service for getting and monitoring battery information
    """
    # Define signals
    battery_info_received = Signal(str, dict)  # device_id, battery_info
    battery_info_error = Signal(str, str)      # device_id, error_message
    battery_command_executed = Signal(str, str, str)  # device_id, command_name, command
    LED_STATUS_MAP = {
        0: "Off", 8: "Off", 16: "Off", 24: "Off",
        1: "Blue", 9: "Blue Blinking", 17: "Blue", 25: "Blue Blinking",
        2: "Green", 10: "Green Blinking", 18: "Green", 26: "Green Blinking",
        3: "Cyan", 11: "Cyan Blinking", 19: "Cyan", 27: "Cyan Blinking",
        4: "Red", 12: "Red Blinking", 20: "Red", 28: "Red Blinking",
        5: "Fuchsia", 13: "Fuchsia Blinking", 21: "Fuchsia", 29: "Fuchsia Blinking",
        6: "Orange", 14: "Orange Blinking", 22: "Orange", 30: "Orange Blinking",
        7: "White", 15: "White Blinking", 23: "White", 31: "White Blinking"
    }

    INTERRUPT_STATUS_MAP = {
        0: "Normal",
        1: "No Battery",
        2: "Timeout",
        8: "Over Temperature - Charge",
        16: "Over Current - Charge",
        24: "Over Current & Temperature - Charge",
        32: "Over Temperature - Discharge",
        64: "Over Current - Discharge",
        96: "Over Current & Temperature - Discharge",
    }

    BATTERY_STATUS_MAP = {
        128: "Charging",
        192: "Discharging",
        160: "Full Charged",
        224: "Full Charged",
        32770: "Initializing",
        32896: "Over Charged",
        16512: "Terminate Charge",
        16544: "Full Charged, Terminate Charge",
        20608: "Over Temperature, Terminate Charge",
        20672: "Over Temperature, Terminate Charge",
        4224: "Over Temperature - Charge",
        4288: "Over Temperature - Discharge",
        3008: "Remaining Capacity and Time Alarm, Terminate Charge",
        960: "Remaining Capacity and Time Alarm",
        704: "Remaining Capacity Alarm",
        448: "Remaining Time Alarm",
    }

    def __init__(self, serial_worker, platform_name="hydra"):
        """
        Initialize Battery Monitor Service
        
        Args:
            serial_worker: Serial worker instance for device communication
            platform_name: Platform name to load appropriate commands
        """
        super().__init__()
        
        self.serial_worker = serial_worker
        self.platform_name = platform_name
        
        # Battery monitoring state
        self.current_device_id = None
        self.is_monitoring = False
        self._is_processing = False  # Track if currently processing commands
        self.collected_battery_info = {}
        self.pending_commands = []
        
        # Current command state for retry mechanism
        self.current_command_name = None
        self.current_command_string = None
        self.retry_counts = {}  # Track retry counts per command
        
        # Load battery commands for the platform
        self._load_battery_commands(platform_name)
        
        # Define command priority (order of execution)
        self.command_priority = [
            "battery_status",
            "top_info",
            "relative_state",
            "voltage",
            "current",
            "temperature",
            "led_status",
            "interrupt_status"
        ]
        
        # Connect to serial worker signals if available
        if self.serial_worker:
            self.serial_worker.command_result.connect(self._on_command_completed)
        
        logger.info(f"Battery Monitor Service initialized for platform: {platform_name}")
    
    def _load_battery_commands(self, platform_name):
        """
        Load battery-related commands from platform command set
        
        Args:
            platform_name: Platform name
        """
        # Initialize platform command set
        self.platform_command_set = PlatformCommandSet(platform_name=platform_name)
        
        # Get battery-related commands only
        self.battery_commands = self._get_battery_commands()
        
        # Add retry mechanism attributes
        self.max_retries = 3    # Maximum number of retries per command
        
        # Define valid ranges for battery values (after conversion)
        self.valid_ranges = {
            "relative_state": (0, 100),     # Battery percentage
            "voltage": (0.0, 15.0),         # Battery voltage (V)
            "current": (-5.0, 5.0),         # Battery current (A)
            "temperature": (0.0, 100.0),    # Battery temperature (°C)
            "led_status": (0, 31),          # Battery LED status
            "interrupt_status": (0, 98),    # Battery interrupt status
            "cpu_usage": (0.0, 100.0),      # CPU usage percentage
            "memory_usage": (0.0, 100.0)    # Memory usage percentage
        }
    
    def _get_battery_commands(self):
        """
        Get battery-related commands from platform command set
        
        Returns:
            Dictionary of battery command names to command strings
        """
        # Get all system info commands from platform command set
        all_commands = self.platform_command_set.get_all_commands(CommandType.SYSTEM_INFO)
        
        # Filter battery-related commands
        battery_command_names = [
            "relative_state",       # Battery state of charge (%)
            "voltage",              # Battery voltage (V)
            "current",              # Battery current (A)
            "temperature",          # Battery temperature (°C)
            "led_status",           # Battery LED status
            "interrupt_status",     # Battery interrupt status
            "battery_status",       # Battery status
            "top_info"              # Top info
        ]
        
        battery_commands = {}
        for cmd_name in battery_command_names:
            if cmd_name in all_commands:
                cmd_value = all_commands[cmd_name]
                if isinstance(cmd_value, list) and len(cmd_value) > 0:
                    battery_commands[cmd_name] = cmd_value[0]
                else:
                    battery_commands[cmd_name] = cmd_value
        
        logger.info(f"Loaded {len(battery_commands)} battery commands: {list(battery_commands.keys())}")
        return battery_commands
    
    def set_platform(self, platform_name: str):
        """
        Set platform name and reload battery commands
        
        Args:
            platform_name: Platform name
        """
        logger.info(f"Setting battery monitor platform to: {platform_name}")
        self.platform_command_set.set_platform(platform_name)
        self.battery_commands = self._get_battery_commands()
    
    def start_battery_monitoring(self, device_id: str) -> bool:
        """
        Start monitoring battery information for specified device
        
        Args:
            device_id: Target device ID
            
        Returns:
            bool: True if monitoring started successfully, False otherwise
        """
        # If already monitoring, return
        if self.pending_commands or self.is_monitoring:
            logger.warning(f"Battery monitoring already in progress for device: {self.current_device_id}")
            return False
        
        logger.info(f"Starting battery monitoring for device: {device_id}")
        self.current_device_id = device_id
        self.collected_battery_info = {}
        
        # Set monitoring flag to True
        self.is_monitoring = True
        self._is_processing = True  # Mark as processing
        
        # Reset retry counters
        self.retry_counts = {}
        self.current_command_name = None
        self.current_command_string = None
        
        # Create prioritized command list
        prioritized_commands = []
        for cmd_name in self.command_priority:
            if cmd_name in self.battery_commands:
                prioritized_commands.append((cmd_name, self.battery_commands[cmd_name]))
        
        # Add any remaining commands not in priority list
        for cmd_name, cmd_value in self.battery_commands.items():
            if cmd_name not in self.command_priority:
                prioritized_commands.append((cmd_name, cmd_value))
        
        self.pending_commands = prioritized_commands
        
        # Start executing the first command
        self._execute_next_command()
        
        return True
    
    def stop_battery_monitoring(self, device_id: str = None):
        """
        Stop the ongoing battery monitoring
        
        Args:
            device_id: The device ID to stop, if None stops the current monitoring
        """
        if device_id and device_id != self.current_device_id:
            logger.debug(f"No active battery monitoring for device {device_id}")
            return
            
        if self.is_monitoring:
            logger.info(f"Stopping battery monitoring for device: {self.current_device_id}")
            
            # Clear the pending commands
            self.pending_commands.clear()
            
            # Reset the monitoring status
            self.is_monitoring = False
            self._is_processing = False  # Clear processing flag
            self.current_device_id = None
            self.collected_battery_info = {}
            
            # Clear retry states
            self.retry_counts = {}
            self.current_command_name = None
            self.current_command_string = None
    
    def get_battery_info_once(self, device_id: str) -> bool:
        """
        Get battery information once without starting continuous monitoring
        
        Args:
            device_id: Target device ID
            
        Returns:
            bool: True if started successfully, False otherwise
        """
        # Check if already monitoring
        if self.is_monitoring:
            logger.warning(f"Battery monitoring already in progress for device: {device_id}")
            return False
        
        if not self.serial_worker:
            logger.error("Serial worker not available")
            return False
        
        logger.info(f"Getting battery info once for device: {device_id}")
        
        # Set up for single reading (temporary monitoring state)
        self.current_device_id = device_id
        self.collected_battery_info = {}
        self.retry_counts = {}
        self.current_command_name = None
        self.current_command_string = None
        
        # Set single reading flag
        self._single_reading_mode = True
        
        # Prepare prioritized command list
        prioritized_commands = []
        for cmd_name in self.command_priority:
            if cmd_name in self.battery_commands:
                prioritized_commands.append((cmd_name, self.battery_commands[cmd_name]))
        
        # Add any remaining commands not in priority list
        for cmd_name, cmd_value in self.battery_commands.items():
            if cmd_name not in self.command_priority:
                prioritized_commands.append((cmd_name, cmd_value))
        
        self.pending_commands = prioritized_commands
        
        # Temporarily set monitoring flag for command execution
        self.is_monitoring = True
        self._is_processing = True  # Mark as processing
        
        # Start executing the first command
        self._execute_next_command()
        
        return True
    
    def _execute_next_command(self):
        """
        Execute the next command in the queue
        """
        if not self.pending_commands or not self.current_device_id:
            # All commands have been executed
            if self.collected_battery_info:
                logger.info(f"Battery info collection completed for device: {self.current_device_id}")
                self.battery_info_received.emit(self.current_device_id, self.collected_battery_info)
            
            # Check if this was a single reading operation
            is_single_reading = getattr(self, '_single_reading_mode', False)
            if is_single_reading:
                self._single_reading_mode = False
            
            # Reset monitoring flag
            self.is_monitoring = False
            self._is_processing = False  # Clear processing flag
            return
        
        # Get the next command to execute (or retry current command)
        if self.current_command_name is None:
            # Get new command from queue
            command_name, command = self.pending_commands.pop(0)
            self.current_command_name = command_name
            self.current_command_string = command
        else:
            # Retry current command
            command_name = self.current_command_name
            command = self.current_command_string
        
        # Emit command executed signal before executing command
        self.battery_command_executed.emit(self.current_device_id, command_name, command)
        
        time.sleep(0.02)  # 50ms delay between battery commands (optimized from 200ms)
        
        # Execute command
        self.serial_worker.send_command(self.current_device_id, command, timeout=10)
    
    def _reset_current_command(self):
        """Reset current command state"""
        self.current_command_name = None
        self.current_command_string = None
    
    def _is_value_in_valid_range(self, command_name: str, value: Any) -> bool:
        """
        Check if the parsed value is within valid range
        
        Args:
            command_name: Command name
            value: Parsed value
            
        Returns:
            bool: True if value is valid, False otherwise
        """
        # Handle top_info command which returns a dictionary
        if command_name == "top_info":
            if not isinstance(value, dict):
                return False
            
            # Check if both cpu_usage and memory_usage are present and valid
            required_keys = ["cpu_usage", "memory_usage"]
            for key in required_keys:
                if key not in value:
                    return False
                
                val = value[key]
                if val is None:
                    return False
                
                # Check if value is within valid range
                if key in self.valid_ranges:
                    min_val, max_val = self.valid_ranges[key]
                    try:
                        if isinstance(val, (int, float)):
                            if not (min_val <= val <= max_val):
                                return False
                        else:
                            return False
                    except (ValueError, TypeError):
                        return False
            
            return True
        
        # Original logic for single value commands
        if command_name not in self.valid_ranges:
            return True  # No range defined, assume valid
        
        if value is None:
            return False
        
        if command_name == "led_status":
            return value in self.LED_STATUS_MAP.keys()
        
        
        try:
            min_val, max_val = self.valid_ranges[command_name]
            if isinstance(value, (int, float)):
                is_in_range = min_val <= value <= max_val
                return is_in_range
            elif isinstance(value, str) and command_name == "pic_firmware":
                # For firmware version strings like "v258"
                if value.startswith("v"):
                    version_num = int(value[1:])
                    is_in_range = min_val <= version_num <= max_val
                    return is_in_range
                return True
        except (ValueError, TypeError) as e:
            pass
        
        return False
    
    def _should_retry_command(self, command_name: str) -> bool:
        """
        Check if command should be retried
        
        Args:
            command_name: Command name
            
        Returns:
            bool: True if should retry, False otherwise
        """
        if command_name not in self.retry_counts:
            self.retry_counts[command_name] = 0
        
        return self.retry_counts[command_name] < self.max_retries
    
    def _increment_retry_count(self, command_name: str):
        """
        Increment retry count for command
        
        Args:
            command_name: Command name
        """
        if command_name not in self.retry_counts:
            self.retry_counts[command_name] = 0
        self.retry_counts[command_name] += 1
    
    @Slot(str, str, str)
    def _on_command_completed(self, device_id: str, command: str, response: str):
        """
        Handle command completion
        
        Args:
            device_id: Device ID
            command: Executed command
            response: Command response
        """
        # Only process commands for current monitoring device
        if device_id != self.current_device_id or not self.is_monitoring:
            return
        
        # Only process if this is the current command being executed
        if command != self.current_command_string:
            return
        
        command_name = self.current_command_name
        if not command_name:
            logger.warning("Received command completion but no current command set")
            return
        
        # Parse the response based on command type
        parsed_value = self._parse_battery_response(command_name, response)
        
        is_valid = parsed_value is not None and self._is_value_in_valid_range(command_name, parsed_value)
        
        # Validate the parsed value
        if is_valid:
            # Valid result, store it
            if command_name == "led_status":
                parsed_value = self.LED_STATUS_MAP[parsed_value]
                self.collected_battery_info[command_name] = parsed_value
            elif command_name == "interrupt_status":
                if parsed_value in self.INTERRUPT_STATUS_MAP.keys():
                    parsed_value = self.INTERRUPT_STATUS_MAP[parsed_value]
                else:
                    logger.warning(f"Interrupt status: {parsed_value}")
                    parsed_value = "Unknown"
                self.collected_battery_info[command_name] = parsed_value
            elif command_name == "battery_status":
                if parsed_value in self.BATTERY_STATUS_MAP.keys():
                    parsed_value = self.BATTERY_STATUS_MAP[parsed_value]
                else:
                    logger.warning(f"Battery status: {parsed_value}")
                    parsed_value = "Unknown"
                self.collected_battery_info[command_name] = parsed_value
            elif command_name == "top_info":
                # For top_info, store individual cpu_usage and memory_usage values
                self.collected_battery_info["cpu_usage"] = parsed_value["cpu_usage"]
                self.collected_battery_info["memory_usage"] = parsed_value["memory_usage"]
            else:
                self.collected_battery_info[command_name] = parsed_value
            
            # Reset current command and continue to next
            self._reset_current_command()
            self._execute_next_command()
            
        else:
            # Invalid result, check if should retry
            if self._should_retry_command(command_name):
                self._increment_retry_count(command_name)
                logger.warning(f"Invalid battery value for {command_name}: {parsed_value}, retrying...")
                
                # Retry current command (don't reset current_command_name)
                self._execute_next_command()
            else:
                # Max retries reached, log error and continue
                logger.error(f"Max retries reached for battery command {command_name}, skipping...")
                self.collected_battery_info[command_name] = None
                
                # Reset current command and continue to next
                self._reset_current_command()
                self._execute_next_command()
    
    def _parse_battery_response(self, command_name: str, response: str) -> Any:
        """
        Parse battery command response
        
        Args:
            command_name: Command name
            response: Command response
            
        Returns:
            Parsed battery value or None if parsing failed
        """
        try:
            # Check for device disconnection errors first
            if "No response received from device" in response or "ClearCommError failed" in response:
                logger.error(f"Device disconnection detected in response for {command_name}: {response}")
                # Emit error signal for device disconnection
                self.battery_info_error.emit(self.current_device_id, response)
                return None
            
            # Process i2ctransfer command results for battery commands
            if command_name in ["relative_state", "voltage", "current", "temperature", "led_status", "interrupt_status", "battery_status"]:
                try:
                    # Enhanced parsing for i2c responses
                    lines = response.strip().split('\n')
                    hex_values = []
                    
                    for line in lines:
                        # Skip command echo lines
                        if 'i2ctransfer' in line or 'sleep' in line or 'root@' in line:
                            continue
                            
                        # Look for hex values in the line
                        if '0x' in line:
                            line_hex = [x.strip() for x in line.split() if x.startswith('0x')]
                            if line_hex:
                                hex_values.extend(line_hex)
                    
                    # Extract the correct hex values for battery commands
                    # Typical i2c response format: 0x02 0xHH 0xLL (status + high byte + low byte)
                    if len(hex_values) >= 3:
                        # Skip the first byte (status byte 0x02) and use the next 2 bytes as data
                        high_byte = int(hex_values[1], 16)  # Second hex value
                        low_byte = int(hex_values[2], 16)   # Third hex value
                        value = (high_byte << 8) + low_byte
                    elif len(hex_values) == 2:
                        # Two values: use both as data (high byte + low byte)
                        high_byte = int(hex_values[0], 16)
                        low_byte = int(hex_values[1], 16)
                        value = (high_byte << 8) + low_byte
                    elif len(hex_values) == 1:
                        # Single value
                        value = int(hex_values[0], 16)
                    else:
                        logger.warning(f"No valid hex values found in response for {command_name}: {response}")
                        return None
                    
                    # Convert format according to different types
                    if command_name == "relative_state":
                        return value  # Battery percentage (0-100)
                    elif command_name == "voltage":
                        # Additional validation for voltage: reject values that look like relative_state
                        if value < 100:  # Values under 100 are likely relative_state contamination
                            logger.warning(f"Voltage value {value} seems too low, likely register contamination")
                            return None
                        return round(float(value/1000), 2)  # Convert to volts
                    elif command_name == "current":
                        # Handle signed 16-bit value: range -32768 to 32767
                        if value > 32767:
                            signed_value = value - 65536  # Convert to signed
                        else:
                            signed_value = value
                        return round(float(signed_value/1000), 2)  # Convert to amperes
                    elif command_name == "temperature":
                        return round(float(value/10)-273.2, 1)  # Convert to Celsius
                    elif command_name == "led_status":
                        return value
                    elif command_name == "interrupt_status":
                        return value
                    elif command_name == "battery_status":
                        return value
                    
                except Exception as e:
                    logger.error(f"Failed to parse battery command {command_name}: {e}")
                    return None
                
            elif command_name == "top_info":
                # Check for device disconnection in top_info response
                if "No response received from device" in response or "ClearCommError failed" in response:
                    logger.error(f"Device disconnection detected in top_info response: {response}")
                    self.battery_info_error.emit(self.current_device_id, response)
                    return None
                # Parse top command output for CPU and memory usage
                return self._parse_top_info_response(response)
            # If it's not a known battery command, return None
            return None
            
        except Exception as e:
            logger.error(f"Error in battery response parsing for {command_name}: {str(e)}")
            return None
        
    def _parse_top_info_response(self, response: str) -> Dict[str, float]:
        """
        Parse top command response to extract CPU and memory usage
        
        Args:
            response: Top command response
            
        Returns:
            Dictionary containing cpu_usage and memory_usage, or None if parsing failed
        """
        try:
            lines = response.strip().split('\n')
            cpu_usage = None
            memory_usage = None
            
            for line in lines:
                line = line.strip()
                
                # Parse CPU usage from lines like: "CPU:  12.5% usr   2.1% sys   0.0% nic  84.4% idle"
                # Or: "%Cpu(s):  5.2 us,  1.3 sy,  0.0 ni, 93.5 id"
                if line.startswith('CPU:') or line.startswith('%Cpu'):
                    try:
                        # Look for patterns like "12.5% usr" or "5.2 us"
                        # Pattern to match percentage values before "usr", "us", "sys", "sy"
                        cpu_pattern = r'(\d+\.?\d*)%?\s*(?:usr|us|sys|sy)'
                        matches = re.findall(cpu_pattern, line)
                        if matches:
                            # Sum up user and system CPU usage (first two matches typically)
                            usr_cpu = float(matches[0]) if len(matches) > 0 else 0.0
                            sys_cpu = float(matches[1]) if len(matches) > 1 else 0.0
                            cpu_usage = round(usr_cpu + sys_cpu, 1)
                            
                            # Alternative: calculate from idle percentage
                            # Look for idle percentage
                            idle_pattern = r'(\d+\.?\d*)%?\s*(?:idle|id)'
                            idle_matches = re.findall(idle_pattern, line)
                            if idle_matches:
                                idle_cpu = float(idle_matches[0])
                                cpu_usage = round(100.0 - idle_cpu, 1)
                    except Exception as e:
                        logger.warning(f"Failed to parse CPU usage from line: {line}, error: {e}")
                
                # Parse memory usage from lines like: "Mem:   1024000k total,   512000k used,   512000k free"
                # Or: "KiB Mem :  2048000 total,  1024000 used,   1024000 free"
                elif 'Mem:' in line or 'KiB Mem' in line:
                    try:
                        # Look for total and used memory values
                        # Pattern to match numbers followed by units (k, M, G, or KiB, MiB, GiB)
                        memory_pattern = r'(\d+)(?:k|K|M|G|KiB|MiB|GiB)?\s+(?:total|used|free)'
                        
                        # Split line and look for total and used values
                        parts = line.split()
                        total_mem = None
                        used_mem = None
                        
                        for i, part in enumerate(parts):
                            if 'total' in part and i > 0:
                                # Previous part should be the total memory value
                                total_str = parts[i-1].replace('k', '').replace('K', '').replace(',', '')
                                total_mem = int(total_str)
                            elif 'used' in part and i > 0:
                                # Previous part should be the used memory value
                                used_str = parts[i-1].replace('k', '').replace('K', '').replace(',', '')
                                used_mem = int(used_str)
                        
                        if total_mem and used_mem and total_mem > 0:
                            memory_usage = round((used_mem / total_mem) * 100.0, 1)
                    except Exception as e:
                        logger.warning(f"Failed to parse memory usage from line: {line}, error: {e}")
            
            # Return result if both values were parsed successfully
            if cpu_usage is not None and memory_usage is not None:
                return {
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage
                }
            else:
                logger.warning(f"Failed to parse top info: cpu_usage={cpu_usage}, memory_usage={memory_usage}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing top info response: {str(e)}")
            return None
    
    def get_battery_commands(self) -> Dict[str, str]:
        """
        Get available battery commands
        
        Returns:
            Dictionary of battery command names to command strings
        """
        return self.battery_commands.copy()
    
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
        self.collected_battery_info = {}
        self.is_monitoring = False
        
        # Clear retry states
        self.retry_counts = {}
        self.current_command_name = None
        self.current_command_string = None
        
        logger.info("Battery Monitor Service cleaned up")


if __name__ == "__main__":
    """
    Test the Battery Monitor Service
    """
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    import sys
    
    # Create application
    app = QApplication(sys.argv)
    
    # Mock serial worker for testing
    class MockSerialWorker(QObject):
        command_result = Signal(str, str, str)
        
        def send_command(self, device_id, command):
            # Simulate battery command responses
            if "0x0d" in command:  # relative_state
                QTimer.singleShot(100, lambda: self.command_result.emit(device_id, command, "0x02 0x00 0x32"))  # 50%
            elif "0x09" in command:  # voltage
                QTimer.singleShot(200, lambda: self.command_result.emit(device_id, command, "0x02 0x1F 0x40"))  # 8V
            elif "0x0a" in command:  # current
                QTimer.singleShot(300, lambda: self.command_result.emit(device_id, command, "0x02 0x07 0xD0"))  # 2A
            elif "0x08" in command:  # temperature
                QTimer.singleShot(400, lambda: self.command_result.emit(device_id, command, "0x02 0x12 0x34"))  # 25°C
    
    # Create mock serial worker
    mock_worker = MockSerialWorker()
    
    # Create battery monitor service
    battery_service = BatteryMonitorService(mock_worker)
    
    # Connect signals for testing
    def on_battery_info_received(device_id, info):
        print(f"Battery info received for {device_id}:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        app.quit()
    
    def on_battery_info_error(device_id, error):
        print(f"Battery info error for {device_id}: {error}")
        app.quit()
    
    battery_service.battery_info_received.connect(on_battery_info_received)
    battery_service.battery_info_error.connect(on_battery_info_error)
    
    # Start battery monitoring
    print("Starting battery monitoring test...")
    battery_service.start_battery_monitoring("test_device")
    
    # Run application
    sys.exit(app.exec()) 