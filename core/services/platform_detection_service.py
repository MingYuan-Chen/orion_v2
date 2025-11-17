from PySide6.QtCore import QObject, Signal, Slot
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger
from typing import List, Dict, Any, Optional

class PlatformDetectionService(QObject):
    """
    A service that detects the platform type of a connected device
    by sending a series of commands and analyzing the responses.
    """
    platform_detected = Signal(str)  # Emits the name of the detected platform

    # --- Configuration ---
    # A list of commands to send. The service will iterate through this list.
    DETECTION_COMMANDS: List[str] = [
        "cat /proc/device-tree/model",
        "strings /dev/mtd0 | grep -E 'U-Boot [0-9]{4}\.'",
        "cat /proc/panel_id",
        # Add more commands here
    ]

    def __init__(self, serial_model: SerialDeviceModel, parent: Optional[QObject] = None):
        """
        Initializes the detection service.
        :param serial_model: The serial device model for communication.
        """
        super().__init__(parent)
        self._model = serial_model
        self._command_index = 0
        self._is_running = False

    def start_detection(self):
        """
        Starts the platform detection sequence.
        Connects to the model's data received signal and sends the first command.
        """
        if self._is_running or not self._model.is_connected():
            if not self._model.is_connected():
                logger.debug("Detection service: Cannot start, model is not connected.")
            return

        logger.debug("Starting platform detection...") # Or use a proper logger
        self._is_running = True
        self._command_index = 0
        self._model.data_received.connect(self._on_data_received)
        self._send_next_command()

    def stop_detection(self):
        """
        Stops the detection sequence and disconnects the signal.
        """
        if not self._is_running:
            return

        logger.debug("Stopping platform detection.")
        self._is_running = False
        try:
            self._model.data_received.disconnect(self._on_data_received)
        except RuntimeError:
            # This can happen if the signal was already disconnected, which is fine.
            pass

    def _send_next_command(self):
        """Sends the next command in the detection sequence."""
        if not self._is_running:
            return

        if self._command_index < len(self.DETECTION_COMMANDS):
            command = self.DETECTION_COMMANDS[self._command_index]
            logger.debug(f"Sending detection command: {command}")
            self._model.send_command(command)
            self._command_index += 1

    @Slot(str)
    def _on_data_received(self, data: str):
        """
        Analyzes incoming data to identify the platform.
        """
        if not self._is_running:
            return
        
        final_detection = None
        if "Athena" in data:
            final_detection = "Athena"
        if "Odin" in data:
            final_detection = "Odin"
        if "00" == data:
            final_detection = "Hydra"
        if "10" == data:
            final_detection = "Gemini FHD"
        if "11" == data:
            final_detection = "Gemini"
        if "01" == data:
            final_detection = "Hydra FHD"
        if "argo" in data:
            final_detection = "Argo"
                

        logger.debug(f"Detection service received: {data}")

        if final_detection:
            logger.info(f"Platform detected: {final_detection}")
            self.platform_detected.emit(final_detection)
            self.stop_detection()
        

        # This simple implementation assumes that a single response is enough
        # to decide whether to send the next command. A more robust version
        # might use a timer to wait for more data before moving on.
        self._send_next_command()
