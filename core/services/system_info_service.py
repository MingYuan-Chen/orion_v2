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
    info_updated = Signal(str, list)  # Emits (info_key, info_value)
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

        cmds = [
            ("uname -a", "#"),
            ("cat /etc/os-release", "#"),
            ("strings /dev/mtd5 | grep -E 'U-Boot [0-9]{4}\\.'", "#"),
            ("lscpu | grep 'Model name'", "#"),
            ("free -h | grep 'Mem:'", "#"),
            ("fdisk -l /dev/mmcblk0", "#"),
            ("top -b -n 1 | head -n 5", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x0d r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x0d r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x15 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x15 r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x14 r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x19 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x19 r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x18 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x18 r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x09 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x09 r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x0a r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x0a r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x21 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x23 0x00 0x14 r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x21 0x00 0x11 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x23 0x00 0x11 r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x16 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x16 r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x08 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x08 r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x1c r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x1c r2", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x51 0x00 0x21 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x53 0x00 0x21 r9", "#"),
            ("i2ctransfer -f -y 1 w4@0x4c 0x03 0x21 0x00 0x10 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x23 0x00 0x10 r2", "#")
        ]
        for cmd, wait_for in cmds:
            response = self._model.send_command_sync(cmd, wait_for, 10)
            self.info_updated.emit(cmd, response)
    
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