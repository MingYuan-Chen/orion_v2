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

    # --- Configuration ---
    COMMANDS: Dict[str, str] = collections.OrderedDict([
        ("cpu_info", "lscpu | grep 'Model name'"),
        ("memory_info", "free -b | grep 'Mem:'"),
        ("top_info", "top -b -n 1 | head -n 5"),
        ("disk_usage", "fdisk -l /dev/mmcblk0"),
        ("relative_state", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x0d r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x0d r2"),
        ("charging_voltage", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x15 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x15 r2"),
        ("charging_current", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x14 r2"),
        ("design_voltage", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x19 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x19 r2"),
        ("design_capacity", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x18 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x18 r2"),
        ("voltage", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x09 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x09 r2"),
        ("current", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x0a r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x0a r2"),
        ("led_status", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x21 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x23 0x00 0x14 r2"),
        ("interrupt_status", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x21 0x00 0x11 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x23 0x00 0x11 r2"),
        ("battery_status", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x16 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x16 r2"),
        ("temperature", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x08 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x08 r2"),
        ("battery_serial", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x1c r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x1c r2"),
        ("battery_model", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x21 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x21 r9"),
        ("pic_firmware", "i2ctransfer -f -y 1 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1;i2ctransfer -f -y 1 w4@0x4c 0x03 0x23 0x00 0x10 r2"),
        ("kernel_version", "uname -a"),
        ("os_version", "cat /etc/os-release"),
        ("uboot_version", "strings /dev/mtd5 | grep -E 'U-Boot [0-9]{4}\\.'")
    ])

    def __init__(self, device_model: SerialDeviceModel, parent: Optional[QObject] = None, platform_name: str = "Unknown"):
        super().__init__(parent)
        self._model = device_model
        self.platform_name = platform_name
        
        self._model.data_received.connect(self._on_data_received)
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
        logger.info("Starting system information collection...")
        
        commands_to_execute = list(self.COMMANDS.values())
        
        for cmd in commands_to_execute:
            self._model.send_command_queued(cmd, "#", 10.0)


    @Slot(list)
    def _on_data_received(self, data: str):
        """
        Slot to handle the completed sequence of responses from the executor.
        """

        try:
            
            # grep cpu info =======================================
            if any(keyword in data.lower() for keyword in ['freescale', 'imx', 'mx6', 'cortex', 'arm', 'intel', 'amd']):
                if self.platform_name == "Athena":
                    self.collected_info['cpu_info'] = {"model": data.split(':')[1].strip()}
                else:
                    self.collected_info['cpu_info'] = {"model": data.strip()}
                self.info_updated.emit('cpu_info', self.collected_info['cpu_info']["model"])
            
            # grep memory info =======================================
            if 'Mem:' in data:
                parts = data.split()
                if len(parts) >= 7:

                    self.collected_info['memory_info'] = {
                        "total": f"{round(float(parts[1])/(1024*1024), 1)} MB",
                        "used": f"{round(float(parts[2])/(1024*1024), 1)} MB",
                        "free": f"{round(float(parts[3])/(1024*1024), 1)} MB",
                        "shared": f"{round(float(parts[4])/(1024*1024), 1)} MB",
                        "buffers": f"{round(float(parts[5])/(1024*1024), 1)} MB",
                        "available": f"{round(float(parts[6])/(1024*1024), 1)} MB",
                        "usage_percent": f"{round((int(parts[2]) / int(parts[1])) * 100, 1)} %"
                    }
                self.info_updated.emit('memory total', self.collected_info['memory_info']["total"])
                self.info_updated.emit('memory used', self.collected_info['memory_info']["used"])
                self.info_updated.emit('memory usage percent', self.collected_info['memory_info']["usage_percent"])

        except Exception as e:
            error_msg = f"An unexpected error occurred during response processing: {e}"
            logger.error(error_msg)
            self.collection_error.emit(error_msg)