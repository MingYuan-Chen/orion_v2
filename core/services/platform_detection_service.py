from PySide6.QtCore import QObject, Signal, Slot
from util.logger import logger
from typing import List, Optional
from core.models.serial_device_model import SerialDeviceModel


class PlatformDetectionService(QObject):
    """
    A service that detects the platform type of a connected device
    by sending a series of commands via the SequenceExecutionService
    and analyzing the aggregated responses.
    """
    platform_detected = Signal(str)
    login_required = Signal(str)

    def __init__(self, device_model: SerialDeviceModel, parent: Optional[QObject] = None):
        """
        Initializes the detection service.
        :param sequence_executor: The service to execute commands.
        """
        super().__init__(parent)
        self._model = device_model
        self._is_running = False

    def start_detection(self):
        """
        Starts the platform detection sequence by running all detection commands.
        """
        
        if not self._ensure_login():
            return

        if self._is_running:
            return

        self._is_running = True
        
        cmds = [
            "cat /proc/device-tree/model",
            "strings /dev/mtd0 | grep -E 'U-Boot [0-9]{4}\\.'",
            "cat /proc/panel_id",
        ]
        for cmd in cmds:
            if not self._is_running:
                break
            
            response = self._model.send_command_sync(cmd, timeout=20)
            self._check_platform(response)

    def stop_detection(self):
        """
        Stops the detection sequence and disconnects signals.
        """
        if not self._is_running:
            return

        self._is_running = False

    def _check_platform(self, data):
        """
        Analyzes the full response from a completed command to identify the platform.
        """
        if not self._is_running:
            return
        
        final_detection = None

        for res in data:
            if "Athena" in res:
                final_detection = "Athena"
            elif "Odin" in res:
                final_detection = "Odin"
            elif "00" == res.strip():
                final_detection = "Hydra"
            elif "10" == res.strip():
                final_detection = "Gemini FHD"
            elif "11" == res.strip():
                final_detection = "Gemini"
            elif "01" == res.strip():
                final_detection = "Hydra FHD"
            elif "argo" in res:
                final_detection = "Argo"
        
        if final_detection:
            logger.info(f"Platform detected: {final_detection}")
            self.platform_detected.emit(final_detection)
            self.stop_detection()
    
    def _ensure_login(self):
        
        retry = 3
        for i in range(retry):
            response = self._model.send_command_sync("root", timeout=2)
            
            for line in response:
                if "root: command not found" in line:
                    return True
            self.login_required.emit(f"Login attempt {i+1} failed: {response}")
        
        self.login_required.emit(f"[ERROR] Device not logged in, stop detection.")
        return False