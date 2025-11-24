import re
import collections
from PySide6.QtCore import QObject, Signal, Slot
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger
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

    COMMANDS = {
        "cpu_info": "lscpu | grep 'Model name'",
        "memory_info": "free -b | grep 'Mem:'",
        "disk_usage": "fdisk -l /dev/mmcblk0",
        "kernel_version": "uname -a",
        "os_version": "cat /etc/os-release",
        "uboot_version": "strings /dev/mtd5 | grep -E 'U-Boot [0-9]{4}\\.'",
        "charging_voltage": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x15 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x15 r2",
        "charging_current": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x14 r2",
        "design_voltage": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x19 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x19 r2",
        "design_capacity": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x18 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x18 r2",
        "battery_serial": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x1c r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x1c r2",
        "battery_model": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x21 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x21 r9",
        "pic_firmware": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x23 0x00 0x10 r2"
    }

    def __init__(self, device_model: SerialDeviceModel, parent: Optional[QObject] = None, platform_name: str = "Unknown"):
        super().__init__(parent)
        self._model = device_model
        self.platform_name = platform_name
        self._is_running = False
        
        self._model.queue_finished.connect(self.collection_finished)
        self.collected_info = {}

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

        for key, cmd in self.COMMANDS.items():
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

        for line in response:
            line.strip()
            if key == "cpu_info":
                cpu_model = "Unknown"
                if any(keyword in line.lower() for keyword in ['freescale', 'imx', 'mx6', 'cortex', 'arm', 'intel', 'amd']):
                    if self.platform_name == "Athena":     
                        cpu_model = line.split(':')[1].strip()
                    else:
                        cpu_model = line.strip()
                    self.info_updated.emit(key, cpu_model)
            elif key == "memory_info":
                memo = "Unknown"
                if 'Mem:' in line:
                    parts = line.split()
                    total = round(float(parts[1])/(1024*1024), 1)
                    used = round(float(parts[2])/(1024*1024), 1)
                    percent = round((used/total)*100, 1)
                    memo = f"Total: {total} MB | Used: {used} MB | Usage: {percent} %"
                    self.info_updated.emit(key, memo)
            
            elif key == "disk_usage":
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
            
            elif key == "kernel_version":
                kernel = "Unknown"
                if 'Linux' in line:
                    kernel = line
                    self.info_updated.emit(key, kernel)
            
            elif key == "os_version":
                os = "Unknown"
                if 'PRETTY_NAME=' in line:
                    os = line.split('=')[1].strip('"')
                    self.info_updated.emit(key, os)
            
            elif key == "uboot_version":
                uboot = "Unknown"
                if 'U-Boot' in line:
                    pattern1 = r'U-Boot\s+([0-9]+\.[0-9]+[^\n]*?\([^)]+\))'
                    match = re.search(pattern1, line)
                    if match:
                        full_version = match.group(1).strip()
                        self.info_updated.emit(key, full_version)
            
            else:
                if len(line) > 4 and line.startswith('0x'):
                    line_hex = [x.replace('0x', '') for x in line.split() if x.startswith('0x')]
                    combined_hex = "0x" + line_hex[0] + line_hex[1]
                    hex_value = int(combined_hex, 16)
                    
                    if key == "charging_voltage":
                        voltage = round(hex_value / 1000, 1)
                        self.info_updated.emit(key, f"{voltage} V")
                    elif key == "charging_current":
                        current = round(hex_value / 1000, 1)
                        self.info_updated.emit(key, f"{current} A")
                    elif key == "design_voltage":
                        voltage = round(hex_value / 1000, 1)
                        self.info_updated.emit(key, f"{voltage} V")
                    elif key == "design_capacity":
                        capacity = hex_value
                        self.info_updated.emit(key, f"{capacity} mAh")
                    elif key == "battery_serial":
                        serial = hex_value
                        self.info_updated.emit(key, f"{hex_value}")
                    elif key == "battery_model" and len(line_hex) >= 4:
                        model = ""
                        for idx in range(1, len(line_hex)):
                            char_code = int(f"0x{line_hex[idx]}", 16)
                            if 32 <= char_code <= 126:
                                model += chr(char_code)
                        self.info_updated.emit(key, model)
                    elif key == "pic_firmware":
                        firmware = hex_value
                        self.info_updated.emit(key, f"v{hex_value}")
                