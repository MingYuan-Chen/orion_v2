"""
System information service module
Provide system information update functionality for dashboard
"""
from PySide6.QtCore import QObject, Signal, Slot, QTimer, QThread
import json
from typing import Dict, Any, Optional, List
from util.logger import logger

class SystemInfoService(QObject):
    """
    System information service
    Provides functionality to get and refresh system information
    """
    # Define signals
    info_received = Signal(str, dict)  # device_id, system_info
    info_error = Signal(str, str)      # device_id, error_message
    
    def __init__(self, serial_worker):
        """
        Initialize system info service
        
        Args:
            serial_worker: Serial device worker for command execution
        """
        super().__init__()
        self.serial_worker = serial_worker
        self.commands = self.get_commands()
        self.pending_commands = []
        self.current_device_id = None
        self.collected_info = {}
        
        # Connect command result signal
        self.serial_worker.command_result.connect(self._on_command_completed)
    
    def get_commands(self):
        """
        Get commands for fetching system information
        """
        return {
            # System basic information
            "cpu_info": "grep 'model name' /proc/cpuinfo | uniq",
            "memory_info": "free -h | grep 'Mem:'",
            "disk_usage": "df -h | grep 'root'",
            
            # Battery information
            "capacity": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x0f r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x0f r2",
            "full_capacity": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x10 r2",
            "relative_state": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x0d r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x0d r2",
            "charging_voltage": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x15 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x15 r2",
            "charging_current": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x14 r2",
            "temperature": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x08 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x08 r2",
            "cycle_count": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x51 0x00 0x17 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x53 0x00 0x17 r2",
            "led_status": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x14 r2",
            "dc_status": "cat /sys/class/gpio/gpio133/value"
        }
    
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
            return
        
        # Get the next command to execute
        command_name, command = self.pending_commands.pop(0)
        
        logger.debug(f"Executing system info command: {command_name} - {command}")
        
        # Execute command and receive result in signal processing
        try:
            self.serial_worker.send_command(self.current_device_id, command, 1)
        except Exception as e:
            logger.error(f"Error sending command {command_name}: {str(e)}")
            self._handle_command_error(command_name, str(e))
    
    @Slot(str, str, str)
    def _on_command_completed(self, device_id: str, command: str, response: str):
        """
        Handle command completion
        
        Args:
            device_id: Device ID
            command: Executed command
            response: Command response
        """
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
            # Continue to execute the next command
            self._execute_next_command()
            return
        
        # Record response
        logger.info(f"Received response for {command_name}:")
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
            else:
                # Store original response
                self.collected_info[command_name] = response
        except Exception as e:
            logger.error(f"Error parsing response for {command_name}: {str(e)}")
            self._handle_command_error(command_name, str(e))
        
        # Execute next command
        self._execute_next_command()
    
    def _handle_command_error(self, command_name: str, error_message: str):
        """
        Handle command error
        
        Args:
            command_name: Name of failed command
            error_message: Error message
        """
        logger.error(f"Command {command_name} failed: {error_message}")
        
        # For specific command errors, send specific signals
        # Here we continue to execute the next command
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
        
        if "model name" in response:
            # Try to extract CPU model
            for line in response.split('\n'):
                if "model name" in line and ":" in line:
                    model = line.split(':', 1)[1].strip()
                    cpu_info["model"] = model
                    break
        
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
    
    def _parse_disk_info(self, response: str) -> Dict[str, Any]:
        """
        Parse disk information from df command with grep 'root'
        
        Args:
            response: Command response
            
        Returns:
            Parsed disk information
        """
        disk_info = {}
        
        lines = response.strip().split('\n')
        for line in lines:
            # Find root file system line, usually contains "/dev/root" and "/"
            if '/dev/root' in line and '/' in line:
                # For response: "/dev/root       3.8G  1.4G  2.2G  38% /"
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        disk_info["filesystem"] = parts[0]         # File system
                        disk_info["total"] = parts[1]              # Total size
                        disk_info["used"] = parts[2]               # Used
                        disk_info["available"] = parts[3]          # Available
                        disk_info["use_percent"] = parts[4].replace('%', '')  # Use rate (remove %)
                        disk_info["mount_point"] = parts[5]        # Mount point
                        
                        # Add type information
                        disk_info["type"] = "eMMC"  # Default assume eMMC
                    except Exception as e:
                        logger.warning(f"Failed to parse disk information: {e}")
                break  # Stop after finding root file system
        
        logger.debug(f"Parsed disk info: {disk_info}")
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
                    # Extract hexadecimal value part
                    value = response.split("r2\n")[1].split("root")[0].split("\n")[1].replace(" 0x", "")
                    value = int(value, 16)
                    
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
                    
                    logger.debug(f"Parsed {command_name}: {parsed_value}")
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
        
        logger.info("System info service cleaned up")


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


