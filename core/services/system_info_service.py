import re
import collections
from PySide6.QtCore import QObject, Signal, Slot
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger
from util.command_loader import CommandLoader
from typing import Dict, Optional, List

class SystemInfoService(QObject):
    """
    A service that collects various system information from a connected device
    by executing a series of commands and parsing the output.
    Works asynchronously with SequenceExecutionService.
    """
    info_updated = Signal(str, str)  # Emits (info_key, info_value)
    collection_finished = Signal()
    collection_error = Signal(str)

    def __init__(self, device_model: SerialDeviceModel, parent: Optional[QObject] = None, platform_name: str = "Unknown"):
        super().__init__(parent)
        self._model = device_model
        self.platform_name = platform_name
        self._is_running = False
        
        self._model.queue_finished.connect(self.collection_finished)
        self.collected_info = {}
        
        # Load commands dynamically
        mapper_folder_name = {
            "Athena": "athena",
            "Odin": "odin",
            "Gemini FHD": "gemini_fhd",
            "Gemini": "gemini",
            "Hydra FHD": "hydra_fhd",
            "Hydra": "hydra",
            "Argo": "argo"
        }
        _mapped_folder_name = mapper_folder_name.get(self.platform_name, "Unknown")
        self.commands = CommandLoader.load_commands(_mapped_folder_name, "system_info")
        if not self.commands:
            logger.warning(f"No system info commands found for platform: {self.platform_name}")

    @Slot()
    def collect_system_info(self):
        """
        Starts the asynchronous collection of system information.
        Results will be processed and emitted once the sequence is complete.

        :param end_marker: The device's command prompt, used to detect the end of a command's output.
        :param timeout_ms: The maximum time (in milliseconds) to wait for a response.
        """
        
        if self._is_running:
            return

        self._is_running = True

        for key, cmd_list in self.commands.items():
            cmd = cmd_list[0] if isinstance(cmd_list, list) and cmd_list else str(cmd_list)
            if key == "uboot_version":
                response = self._model.send_command_sync(cmd, timeout=20)
            else:
                response = self._model.send_command_sync(cmd)
            self._parse_info(key, response)
    
    def stop_collection(self):
        """
        Stops the collection and disconnects signals.
        """
        if not self._is_running:
            return

        self._is_running = False
        try:
            # Disconnect from all signals from the sequence executor
            self._model.queue_finished.disconnect(self.collection_finished)
        except RuntimeError:
            logger.warning("Error disconnecting signals from SerialDeviceModel.")
    
    def _parse_info(self, key, response):

        model = None
        cpu_count = None
        max_mhz_raw = None
        
        if key == "Main_Processor" and "odin" in self.platform_name.lower():
            model = response[1]
            frequency = int(response[2])
            processor = response[3]

            frequency = frequency / 1000000
            cpu_model = f"{model} @ {frequency:.2f} GHz ({processor} cores)"
            logger.error (response)
            self.info_updated.emit(key, cpu_model)

        for line in response:
            line.strip()
            if "Main_Processor" in key:
                cpu_model = "Unknown"
                if "athena" in self.platform_name.lower() and ":" in line:
                    result = line.split(":", 1)
                    if result[0] == "Model name":
                        model = result[1].strip()
                    if result[0] == "CPU(s)":
                        cpu_count = result[1].strip()
                    if result[0] == "CPU max MHz":
                        max_mhz_raw = round(float(result[1].strip())/1000, 2)
                if model and cpu_count and max_mhz_raw:
                    cpu_model = f"{model} @ {max_mhz_raw} GHz ({cpu_count} cores)"
                    self.info_updated.emit(key, cpu_model)
            elif "Memory" in key:
                memo = "Unknown"
                if 'Mem:' in line:
                    parts = line.split()
                    try:
                        total_bytes = self._parse_memory_value(parts[1])
                        used_bytes = self._parse_memory_value(parts[2])
                        
                        total_mb = round(total_bytes / (1024 * 1024), 1)
                        used_mb = round(used_bytes / (1024 * 1024), 1)
                        
                        if total_bytes > 0:
                            percent = round((used_bytes / total_bytes) * 100, 1)
                        else:
                            percent = 0.0
                            
                        memo = f"Total: {total_mb} MB | Used: {used_mb} MB | Usage: {percent} %"
                        self.info_updated.emit(key, memo)
                    except Exception as e:
                        logger.error(f"Error parsing memory info: {e}")
                        self.info_updated.emit(key, f"Error: {line}")


            elif "Storage" in key:
                disk = "Unknown"
                if self.platform_name == "Athena" and "Disk /dev/mmcblk0:" in line:
                    disk = line.split(',')[0].split(':')[1].strip()
                    dist = f"Total: 128 GiB | Available: {disk}"
                    self.info_updated.emit(key, dist)
                else:
                    if line.isdigit():
                        t_sectors = int(line)
                        t_bytes = t_sectors * 512
                        disk = round(t_bytes/(1024*1024*1024), 2)
                        if 50 < disk < 80:
                            total_string = "64 GiB"
                        elif disk < 40:
                            total_string = "32 GiB"
                        else:
                            total_string = "128 GiB"

                        dist = f"Total: {total_string} | Available: {disk} GiB"
                        self.info_updated.emit(key, dist)
            
            elif "Kernel_Version" in key:
                kernel = "Unknown"
                if 'Linux' in line:
                    kernel = line
                    self.info_updated.emit(key, kernel)
            
            elif "OS_Version" in key:
                os = "Unknown"
                if 'PRETTY_NAME=' in line:
                    os = line.split('=')[1].strip('"')
                    self.info_updated.emit(key, os)
            
            elif "UBoot_Version" in key:
                uboot = "Unknown"
                if 'U-Boot' in line and "athena" in self.platform_name.lower():
                    pattern1 = r'U-Boot\s+([0-9]+\.[0-9]+[^\n]*?\([^)]+\))'
                    match = re.search(pattern1, line)
                    if match:
                        full_version = match.group(1).strip()
                        self.info_updated.emit(key, full_version)
                if "U-Boot" in line and "odin" in self.platform_name.lower():
                    pattern1 = r'(U-Boot SPL\s+[^\(]+\([^)]+\))'
                    match = re.search(pattern1, line)
                    if match:
                        full_version = match.group(1).strip()
                        self.info_updated.emit(key, full_version)

            else:
                if len(line) > 4 and line.startswith('0x'):
                    line_hex = [x.replace('0x', '') for x in line.split() if x.startswith('0x')]
                    combined_hex = "0x" + line_hex[0] + line_hex[1]
                    hex_value = int(combined_hex, 16)
                    
                    if isinstance(hex_value, int) and hex_value == 0xFFFF:
                        self.info_updated.emit(key, "No Battery Detected")
                        return
                    if "Charging_Voltage" in key:
                        voltage = round(hex_value / 1000, 1)
                        self.info_updated.emit(key, f"{voltage} V")
                    elif "Charging_Current" in key:
                        current = round(hex_value / 1000, 1)
                        self.info_updated.emit(key, f"{current} A")
                    elif "Normal_Voltage" in key:
                        voltage = round(hex_value / 1000, 1)
                        self.info_updated.emit(key, f"{voltage} V")
                    elif "Typical_Capacity" in key:
                        capacity = hex_value
                        self.info_updated.emit(key, f"{capacity} mAh")
                    elif "Battery_S/N" in key:
                        serial = hex_value
                        self.info_updated.emit(key, f"{hex_value}")
                    elif "Battery_Model" in key and len(line_hex) >= 4:
                        model = ""
                        for idx in range(1, len(line_hex)):
                            char_code = int(f"0x{line_hex[idx]}", 16)
                            if 32 <= char_code <= 126:
                                model += chr(char_code)
                        self.info_updated.emit(key, model)
                    elif "PIC_Version" in key:
                        firmware = hex_value
                        self.info_updated.emit(key, f"v{firmware}")

    def _parse_memory_value(self, value_str: str) -> float:
        """Parses a memory string (e.g., '3.8Gi', '1024', '500M') into bytes."""
        value_str = value_str.strip()
        units = {
            'Ti': 1024**4, 'Gi': 1024**3, 'Mi': 1024**2, 'Ki': 1024,
            'T': 1024**4, 'G': 1024**3, 'M': 1024**2, 'K': 1024,
            'B': 1
        }
        
        for unit, factor in units.items():
            if value_str.endswith(unit):
                try:
                    number_part = value_str[:-len(unit)]
                    return float(number_part) * factor
                except ValueError:
                    continue
        
        # If no unit found or parsing failed, try parsing as raw number (bytes)
        try:
            return float(value_str)
        except ValueError:
            return 0.0