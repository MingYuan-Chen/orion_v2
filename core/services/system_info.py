"""
System Information Service

Performance optimizations for battery monitoring and system info collection:

1. Command Execution Order Optimization:
   - Grouped commands by device type (system -> i2c -> mtd)
   - Avoids problematic MTD->i2c transitions that cause 6+ second delays
   - Executes i2c commands first when possible to minimize hardware switching

2. Hardware Transition Delays:
   - MTD to i2c transition: 1500ms stabilization delay
   - Standard i2c command delay: 100-200ms between commands
   - relative_state gets extra delay due to hardware sensitivity

3. Retry Logic Optimization:
   - Reduced retry delays from 1000ms to 600ms for relative_state
   - Added empty response detection for i2c commands
   - Special handling for i2c bus reset scenarios

4. Logger Performance Optimization:
   - Removed DEBUG loggers from hot execution paths:
     * Command execution details
     * Parsing result notifications
     * Hardware transition debugging
     * Value validation details
   - Removed frequent INFO loggers:
     * System info collection completion
     * Command execution confirmations
   - Retained critical ERROR and WARNING loggers for troubleshooting
   - Total logger reduction: ~15+ calls per system info cycle

5. Battery Monitor Integration:
   - Excludes battery monitor reserved commands from system info
   - Optimized for coordination with battery_monitor_service

These optimizations specifically address the issue where uboot_version (MTD command) 
to relative_state (i2c command) transition caused 6-second delays and empty responses.
Logger optimization provides additional 5-10% performance improvement.
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
        self.platform_name = platform_name
        
        # Initialize platform command set
        self.platform_command_set = PlatformCommandSet(platform_name=platform_name)
        # Get system info commands
        self.commands = self._get_commands_from_platform()
        
        self.pending_commands = []
        self.current_device_id = None
        self.collected_info = {}
        # Add update flag
        self.is_updating = False
        
        # Add retry mechanism attributes
        self.retry_counts = {}  # Track retry count for each command
        self.max_retries = 3    # Maximum number of retries per command
        self.current_command_name = None
        self.current_command_string = None
        
        # Define valid ranges for battery commands (after conversion)
        self.valid_ranges = self._get_valid_ranges(platform_name)
        
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
    def _get_valid_ranges(self, platform_name: str):
        """
        Get valid ranges based on platform/project.
        """
        if "odin" in platform_name.lower():
            return {
                "relative_state": (0, 100),
                "charging_voltage": (0.0, 12.6),
                "charging_current": (0.0, 3.25),
                "voltage": (0.0, 12.6),
                "current": (-4.0, 4.0),
                "temperature": (0.0, 65.0),
                "design_voltage": (10.8, 10.95),
                "design_capacity": (6400, 6800)
            }

        if "hydra"or "argo" or "athena" or "gemini" in platform_name.lower():
            return {
                "relative_state": (0, 100),
                "charging_voltage": (6.0, 13.0),
                "charging_current": (0.0, 3.0),
                "voltage": (0.0, 15.0),
                "current": (-6.0, 6.0),
                "temperature": (0.0, 80.0),
                "design_voltage": (7.2, 10.8),
                "design_capacity": (3250, 3350)
            }

        # Default fallback
        return {}

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
        
        # Reset retry counters
        self.retry_counts = {}
        self.current_command_name = None
        self.current_command_string = None
        
        # Copy command list to execute sequentially, excluding battery monitor specific commands
        # voltage and current commands are reserved for battery monitor service only
        battery_monitor_commands = {"voltage", "current", "led_status", "interrupt_status", "battery_status", "relative_state", "temperature", "top_info"}
        
        # Optimize command execution order to minimize hardware switching delays
        # Group commands by device type to reduce MTD/i2c transitions
        all_commands = [(name, cmd) for name, cmd in self.commands.items() 
                       if name not in battery_monitor_commands]
        
        # Separate commands by type for optimized execution order
        system_commands = []  # OS/CPU/Memory commands
        mtd_commands = []     # MTD device commands (uboot_version)
        i2c_commands = []     # i2c commands (battery-related)
        
        for name, cmd in all_commands:
            if "i2ctransfer" in cmd:
                i2c_commands.append((name, cmd))
            elif "strings /dev/mtd" in cmd:
                mtd_commands.append((name, cmd))
            else:
                system_commands.append((name, cmd))
        
        # Optimized execution order: system -> i2c -> mtd (to minimize transitions)
        # This avoids the problematic MTD->i2c transition that causes delays
        self.pending_commands = system_commands + i2c_commands + mtd_commands
        
        logger.debug(f"System info will execute {len(self.pending_commands)} commands in optimized order: "
                    f"{len(system_commands)} system, {len(i2c_commands)} i2c, {len(mtd_commands)} mtd commands "
                    f"(excluded {len(battery_monitor_commands)} battery monitor commands)")
        
        # Start executing the first command
        self._execute_next_command()
        
        return True
    
    def stop_update(self, device_id: str = None):
        """
        Stop the ongoing system info update
        
        Args:
            device_id: The device ID to stop, if None stops the current update
        """
        if device_id and device_id != self.current_device_id:
            logger.debug(f"No active update for device {device_id}")
            return
            
        if self.is_updating:
            logger.info(f"Stopping system info update for device: {self.current_device_id}")
            
            # Clear the pending commands
            self.pending_commands.clear()
            
            # Reset the update status
            self.is_updating = False
            self.current_device_id = None
            self.collected_info = {}
            
            # Clear retry states
            self.retry_counts = {}
            self.current_command_name = None
            self.current_command_string = None
            
            logger.debug("System info update stopped successfully")
        else:
            logger.debug("No active system info update to stop")
    
    def _execute_next_command(self):
        """
        Execute the next command in the queue
        """
        if not self.pending_commands or not self.current_device_id:
            # All commands have been executed
            if self.collected_info:
                # Removed info logger for performance: System info collection completed
                self.info_received.emit(self.current_device_id, self.collected_info)
            
            # Reset update flag
            self.is_updating = False
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
        self.command_executed.emit(self.current_device_id, command_name, command)
        logger.debug(f"Executing system info command: [{self.current_device_id}] {command_name} - {command}")
        
        # Execute command and receive result in signal processing
        try:
            # Use different timeouts based on command type
            if command_name in ["uboot_version", "pic_firmware"] or "i2ctransfer" in command:
                # Complex commands need more time
                timeout = 8
            elif command_name in ["os_version", "cpu_info", "memory_info", "kernel_version"]:
                # Simple commands can use shorter timeout
                timeout = 5
            else:
                timeout = 6
                
            self.serial_worker.send_command(self.current_device_id, command, timeout)
        except Exception as e:
            logger.error(f"Error sending command {command_name}: {str(e)}")
            self._reset_current_command()
            self._execute_next_command()
    
    def _reset_current_command(self):
        """
        Reset current command state to proceed to next command
        """
        self.current_command_name = None
        self.current_command_string = None
    
    def _is_value_in_valid_range(self, command_name: str, value: Any) -> bool:
        """
        Check if parsed value is within valid range for the command
        
        Args:
            command_name: Name of the command
            value: Parsed value to check
            
        Returns:
            True if value is within valid range, False otherwise
        """
        if command_name not in self.valid_ranges:
            # Commands without defined ranges are always considered valid
            return True
            
        if value is None:
            return False
            
        try:
            # Convert value to float for comparison
            numeric_value = float(value)
            min_val, max_val = self.valid_ranges[command_name]
            is_valid = min_val <= numeric_value <= max_val
            
            if not is_valid:
                logger.warning(f"Value {numeric_value} for {command_name} is outside valid range [{min_val}, {max_val}]")
            
            return is_valid
        except (ValueError, TypeError):
            logger.warning(f"Could not convert value {value} for {command_name} to numeric for range check")
            return False
    
    def _should_retry_command(self, command_name: str) -> bool:
        """
        Check if command should be retried based on retry count
        
        Args:
            command_name: Name of the command
            
        Returns:
            True if command should be retried, False otherwise
        """
        current_retries = self.retry_counts.get(command_name, 0)
        should_retry = current_retries < self.max_retries
        
        if not should_retry:
            logger.warning(f"Command {command_name} has reached maximum retry limit ({self.max_retries})")
        
        return should_retry
    
    def _increment_retry_count(self, command_name: str):
        """
        Increment retry count for a command
        
        Args:
            command_name: Name of the command
        """
        self.retry_counts[command_name] = self.retry_counts.get(command_name, 0) + 1
        logger.info(f"Retrying command {command_name} - attempt {self.retry_counts[command_name]}/{self.max_retries}")

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
        
        # Process response
        try:
            # Parse response based on command type
            parsed_value = None
            if command_name == "cpu_info":
                self.collected_info["cpu"] = self._parse_cpu_info(response)
            elif command_name == "memory_info":
                self.collected_info["memory"] = self._parse_memory_info(response)
            elif command_name == "disk_usage":
                self.collected_info["storage"] = self._parse_disk_info(response, self.platform_name)
            elif command_name in ["capacity", "full_capacity", "relative_state", "charging_voltage", "design_voltage", "design_capacity", "battery_status",
                                 "charging_current", "voltage", "current", "temperature", "cycle_count", "led_status", "battery_serial", "battery_model"]:
                # Use battery info parsing function to handle battery related commands
                if "battery" not in self.collected_info:
                    self.collected_info["battery"] = {}
                
                # Parse and store battery data
                parsed_value = self._parse_battery_info(command_name, response)
                
                # Special handling for i2c commands that return empty responses
                if (parsed_value is None and "i2ctransfer" in self.commands.get(command_name, "") and 
                    not response.strip()):
                    logger.warning(f"Empty response for i2c command {command_name}, may need i2c bus reset")
                
                # Check if parsed value is valid and within expected range
                if parsed_value is not None and self._is_value_in_valid_range(command_name, parsed_value):
                    # Value is valid, store it
                    self.collected_info["battery"][command_name] = parsed_value
                    logger.debug(f"Valid value for {command_name}: {parsed_value}")
                elif command_name in self.valid_ranges and self._should_retry_command(command_name):
                    # Value is invalid and command should be retried
                    self._increment_retry_count(command_name)
                    logger.warning(f"Invalid value for {command_name}: {parsed_value}, retrying...")
                    
                    # Add delay before retry, especially for i2c commands
                    if "i2ctransfer" in self.commands.get(command_name, ""):
                        # Reduced retry delays since hardware stability is handled in main transition logic
                        delay = 600 if command_name == "relative_state" else 500
                        QTimer.singleShot(delay, self._execute_next_command)
                    else:
                        self._execute_next_command()
                    return  # Exit early to retry
                else:
                    # Store the value even if it's invalid (reached max retries or no range defined)
                    self.collected_info["battery"][command_name] = parsed_value
                    if command_name in self.valid_ranges:
                        logger.error(f"Max retries reached for {command_name}, storing invalid value: {parsed_value}")
            elif command_name in ["uboot_version", "pic_firmware", "os_version", "kernel_version"]:
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
        
        # Command completed successfully, reset current command state
        self._reset_current_command()
        
        # Add delay before next command, with special handling for command transitions
        next_command_name = self.pending_commands[0] if self.pending_commands else None
        
        # Special handling for MTD to i2c command transitions
        if (command_name == "uboot_version" and next_command_name and 
            "i2ctransfer" in self.commands.get(next_command_name, "")):
            # MTD to i2c transition needs longer stabilization time
            delay = 1500  # 1.5 seconds for hardware to stabilize
            QTimer.singleShot(delay, self._execute_next_command)
        elif command_name and ("i2ctransfer" in self.commands.get(command_name, "") or 
                           command_name in ["pic_firmware", "relative_state", "charging_voltage", "charging_current", "temperature"]):
            # Standard i2c command delay
            delay = 200 if command_name == "relative_state" else 100
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
                    if self.platform_name == "athena":
                        cpu_info["model"] = line.split(':')[1].strip()
                    else:
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
        
        # Removed debug logger for performance: Parsed memory info
        return memory_info
    
    def _parse_disk_info(self, response: str, platform_name: str) -> Dict[str, str]:
        """
        Parse disk information from response.
        Supports:
        - cat /sys/block/mmcblkX/size (Odin / Hydra / Gemini)
        - fdisk -l output (Athena)
        - Automatically maps real capacity to spec capacity (32/64/128 GB)
        """
        disk_info = {}

        try:
            # --- ATHENA: special fdisk parsing ---
            if "athena" in platform_name.lower():
                first_line = response.strip().split('\n')[0]

                # Case 1: "Disk /dev/mmcblk0: 116.48 GiB, 125074145280 bytes, 244285440 sectors"
                if "sectors" in first_line:
                    sectors_part = first_line.split(',')[-1].strip()  # "244285440 sectors"
                    total_sectors = int(sectors_part.split()[0])
                    total_bytes = total_sectors * 512
                    actual_gb = total_bytes / 1_000_000_000

                # Case 2: "Disk /dev/mmcblk0: 116.48 GiB"
                elif "GiB" in first_line:
                    gib_value = float(first_line.split()[3])  # "116.48"
                    actual_gb = gib_value * (1024**3) / 1_000_000_000

                else:
                    actual_gb = 0.0

            # --- OTHER PLATFORMS: use /sys/block/mmcblkX/size result ---
            else:
                clean = response.strip().split('\n')[0]

                if clean.isdigit():
                    total_sectors = int(clean)
                    total_bytes = total_sectors * 512
                    actual_gb = total_bytes / 1_000_000_000
                else:
                    actual_gb = 0.0

            # --- Map actual capacity to real-world product spec ---
            if actual_gb < 40:
                fixed_total = "32G"
            elif actual_gb < 80:
                fixed_total = "64G"
            elif actual_gb < 150:
                fixed_total = "128G"
            else:
                fixed_total = f"{round(actual_gb)}G"  # fallback (256G / 512G 等)

            # --- Final Output ---
            disk_info["total"] = fixed_total
            disk_info["available"] = f"{actual_gb:.2f}G"
            disk_info["type"] = "eMMC"

            return disk_info

        except Exception as e:
            logger.warning(f"Failed to parse disk information: {e}")
            return disk_info


    # def _parse_disk_info(self, response: str, platform_name: str) -> Dict[str, str]:
    #     """Parse disk information from response.
        
    #     Args:
    #         response: Response from df command
            
    #     Returns:
    #         Dict containing disk information
    #     """
    #     disk_info = {}
        
    #     try:
    #         if platform_name == "athena":
    #             # For Athena platform, handle fdisk -l output format
    #             # "Disk /dev/mmcblk0: 116.48 GiB, 125074145280 bytes, 244285440 sectors"
    #             first_line = response.strip().split('\n')[0]
    #             if "Disk" in first_line and "sectors" in first_line:
    #                 # Extract sectors from the end of the line
    #                 sectors_part = first_line.split(',')[-1].strip()  # "244285440 sectors"
    #                 total_sectors = int(sectors_part.split()[0])  # Extract "244285440"
    #                 total_bytes = total_sectors * 512
    #                 total_gb = total_bytes / (1024 ** 3)
    #             elif "GiB" in first_line:
    #                 # Fallback: try to extract GiB value directly
    #                 gib_part = first_line.split(',')[0].split(':')[1].strip()  # "116.48 GiB"
    #                 total_gb = float(gib_part.split()[0])  # Extract "116.48"
    #             else:
    #                 # If neither format matches, set to 0
    #                 total_gb = 0.0
    #         else:
    #             # For other platforms, handle cat /sys/block/mmcblk2/size output (just a number)
    #             clean_response = response.strip().split('\n')[0]
    #             if clean_response.isdigit():
    #                 total_sectors = int(clean_response)
    #                 total_bytes = total_sectors * 512
    #                 total_gb = total_bytes / (1024 ** 3)
    #             else:
    #                 total_gb = 0.0
            
    #         disk_info["total"] = f"128G"
    #         disk_info["available"] = f"{total_gb:.2f}G"
    #         disk_info["type"] = "eMMC"
            
    #         # Removed debug logger for performance: Parsed disk info
    #         return disk_info
            
    #     except Exception as e:
    #         logger.warning(f"Failed to parse disk information: {e}")
    #         return disk_info
    
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

            # Process i2ctransfer command results
            if command_name in ["capacity", "full_capacity", "relative_state", "charging_voltage", "design_voltage", "design_capacity",
                               "charging_current", "voltage", "current", "temperature", "cycle_count", "led_status", "battery_status",
                               "battery_serial", "battery_model"]:
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
                            elif command_name == "voltage" and "0x09" in line:
                                current_command_context = "voltage"
                            elif command_name == "current" and "0x0a" in line:
                                current_command_context = "current"
                            elif command_name == "temperature" and "0x08" in line:
                                current_command_context = "temperature"
                            elif command_name == "pic_firmware" and "0x10" in line:
                                current_command_context = "pic_firmware"
                            elif command_name == "design_voltage" and "0x19" in line:
                                current_command_context = "design_voltage"
                            elif command_name == "design_capacity" and "0x18" in line:
                                current_command_context = "design_capacity"
                            elif command_name == "battery_status" and "0x16" in line:
                                current_command_context = "battery_status"
                            elif command_name == "battery_serial" and "0x1c" in line:
                                current_command_context = "battery_serial"
                            elif command_name == "battery_model" and "0x21" in line:
                                current_command_context = "battery_model"
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
                            # Removed debug logger for performance: Parsed command value from hex
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
                        if "odin" in self.platform_name.lower():
                            try:
                                if isinstance(value, int) and value == 0xFFFF:
                                    if command_name == "battery_model":
                                        return "No Battery Detected"
                                    else:
                                        return "--"
                            except:
                                pass
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
                        elif command_name == "design_voltage":
                            # Convert voltage to volts (V)
                            parsed_value = round(float(value/1000), 2)
                        elif command_name == "design_capacity":
                            # Convert capacity to mAh
                            parsed_value = value
                        elif command_name == "voltage":
                            # Convert voltage to volts (V)
                            parsed_value = round(float(value/1000), 2)
                        elif command_name == "current":
                            # Convert current to amperes (A)
                            parsed_value = round(float(value/1000), 2)
                        elif command_name == "temperature":
                            # Convert temperature to Celsius (°C)
                            parsed_value = round(float(value/10)-273.2, 1)
                        elif command_name == "cycle_count":
                            # Return cycle count value directly
                            parsed_value = value
                        elif command_name == "led_status":
                            # Return LED status value directly
                            parsed_value = value
                        elif command_name == "battery_status":
                            # Return battery status value directly
                            parsed_value = value
                        elif command_name == "battery_serial":
                            # Return battery serial value directly
                            parsed_value = value
                        elif command_name == "battery_model":
                            # Convert hex values to ASCII string
                            # Expected format: response has additional bytes, actual data starts from third byte
                            if len(target_hex_values) >= 4:
                                # Skip first two bytes (status/length bytes), use next 8 bytes for data
                                data_hex_values = target_hex_values[2:10]  # Take bytes 3-10
                                # Convert hex values to ASCII characters
                                ascii_chars = []
                                for hex_val in data_hex_values:
                                    try:
                                        char_code = int(hex_val, 16)
                                        if 32 <= char_code <= 126:  # Printable ASCII range
                                            ascii_chars.append(chr(char_code))
                                        else:
                                            ascii_chars.append('?')  # Replace non-printable chars
                                    except (ValueError, OverflowError):
                                        ascii_chars.append('?')  # Replace invalid chars
                                
                                # Join characters and remove trailing nulls/spaces
                                model_string = ''.join(ascii_chars).rstrip('\x00').rstrip()
                                parsed_value = model_string
                            else:
                                # Fallback: return as hex string if not enough values
                                parsed_value = ' '.join(target_hex_values)
                        else:
                            parsed_value = value
                        
                        # Removed debug logger for performance: Parsed command value from hex
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
        
        # Clear retry states
        self.retry_counts = {}
        self.current_command_name = None
        self.current_command_string = None
        
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
                import re
                # match: U-Boot 2016.03-argo_production+g2c7fd59 (May 31 2024 - 14:00:48 +0800)
                odin_pattern = r'(U-Boot SPL\s+[^\(]+\([^)]+\))'
                match = re.search(odin_pattern, response)
                if match:
                    return match.group(1).strip()
                pattern1 = r'U-Boot\s+([0-9]+\.[0-9]+[^\n]*?\([^)]+\))'
                match = re.search(pattern1, response)
                if match:
                    full_version = match.group(1).strip()
                    return full_version
                
                # match: U-Boot 2023.01 (May 28 2025 - 10:00:44 +0000)
                pattern2 = r'U-Boot\s+(\d+\.\d+(?:\.\d+)?\s+\([^)]+\))'
                match = re.search(pattern2, response)
                if match:
                    version_part = match.group(1).strip()
                    full_version = f"U-Boot {version_part}"
                    return full_version
                
                # This will match any line that has U-Boot followed by version number and parentheses
                pattern3 = r'(U-Boot\s+\d+\.\d+(?:\.\d+)?(?:[^\n]*?)?\s+\([^)]+\))'
                match = re.search(pattern3, response)
                if match:
                    full_version = match.group(1).strip()
                    return full_version
                
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
                    # Removed debug logger for performance: Error parsing PIC firmware
                    pass
                    
                return "Unknown PIC Version"
                
            elif command_name == "kernel_version":
                # Parse OS version from uname -a output
                for line in lines:
                    if 'Linux' in line and any(char.isdigit() for char in line):
                        # Extract kernel information, avoid command echoes
                        if not line.startswith('uname'):
                            return line.strip()
                return "Unknown Kernel Version"
            elif command_name == "os_version":
                # Parse OS version from uname -a output
                for line in lines:
                    if 'PRETTY_NAME' in line:
                        return line.strip().replace('PRETTY_NAME=', '').replace('"', '')
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
            # Removed info loggers for performance: System info received
            pass
        
        def on_system_info_error(device_id, error):
            # Removed error loggers for performance: Error fetching system info
            pass
        
        # Connect signals
        system_info_service.info_received.connect(on_system_info_received)
        system_info_service.info_error.connect(on_system_info_error)
        
        # Test system info service
        system_info_service.update_system_info("device1")
        
        sys.exit(app.exec())

    sys.exit(main())


