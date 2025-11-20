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

    DETECTION_COMMANDS: List[str] = [
        "cat /proc/device-tree/model",
        "strings /dev/mtd0 | grep -E 'U-Boot [0-9]{4}\\.'",
        "cat /proc/panel_id",
    ]

    def __init__(self, device_model: SerialDeviceModel, parent: Optional[QObject] = None):
        """
        Initializes the detection service.
        :param sequence_executor: The service to execute commands.
        """
        super().__init__(parent)
        self._model = device_model
        self._is_running = False
        
        self._model.data_received.connect(self._on_data_received)

    def start_detection(self):
        """
        Starts the platform detection sequence by running all detection commands.
        """
        if self._is_running:
            return

        self._is_running = True
        
        for cmd in self.DETECTION_COMMANDS:
            self._model.send_command_queued(cmd)

    def stop_detection(self):
        """
        Stops the detection sequence and disconnects signals.
        """
        if not self._is_running:
            return

        self._is_running = False
        try:
            # Disconnect from all signals from the sequence executor
            self._model.data_received.disconnect(self._on_data_received)
        except RuntimeError:
            logger.warning("Error disconnecting signals from SerialDeviceModel.")

    @Slot(str)
    def _on_data_received(self, data: str):
        """
        Analyzes the full response from a completed command to identify the platform.
        """
        if not self._is_running:
            return
        
        logger.debug(f"Detection service received response: {data}")
        
        final_detection = None
        if "Athena" in data:
            final_detection = "Athena"
        elif "Odin" in data:
            final_detection = "Odin"
        elif "00" == data.strip():
            final_detection = "Hydra"
        elif "10" == data.strip():
            final_detection = "Gemini FHD"
        elif "11" == data.strip():
            final_detection = "Gemini"
        elif "01" == data.strip():
            final_detection = "Hydra FHD"
        elif "argo" in data:
            final_detection = "Argo"
        
        if final_detection:
            logger.info(f"Platform detected: {final_detection}")
            self.platform_detected.emit(final_detection)
            self.stop_detection()