
import sys
from typing import List, Optional, Dict
from PySide6.QtCore import QObject, Signal, Slot, Property, QStringListModel, Qt
from core.models.serial_device_model import SerialDeviceModel
from core.services.platform_detection_service import PlatformDetectionService
from core.services.system_info_service import SystemInfoService
from util.logger import logger

class DeviceViewModel(QObject):
    """
    ViewModel for the serial device view. It mediates between the View and the Model.
    """
    def __init__(self, model: SerialDeviceModel, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._model = model
        self._log_text = ""
        self._command_text = ""
        self._is_connected = False
        self._platform_name = "Unknown"
        self._system_info = {}
        self._system_info_service = None

        # --- Port list management ---
        self._port_list_model = QStringListModel()
        self.refresh_ports()

        # --- Services ---
        self._detection_service = PlatformDetectionService(device_model=self._model)

        # --- Connect signals from the model to ViewModel slots ---
        self._model.connection_result.connect(self.on_connection_result)
        self._model.disconnection_result.connect(self.on_disconnection_result)
        self._model.data_received.connect(self.on_data_received)
        self._detection_service.platform_detected.connect(self.on_platform_detected)

    # =================================================================================
    # Signals to notify the View of property changes
    # =================================================================================
    log_text_changed = Signal()
    is_connected_changed = Signal()
    command_text_changed = Signal()
    platform_name_changed = Signal()
    system_info_changed = Signal(str, str)
    system_info_reset = Signal()
    system_info_keys_changed = Signal()
    open_system_info_requested = Signal()

    # =================================================================================
    # Properties accessible by the View
    # =================================================================================
    @Property(str, notify=log_text_changed)
    def log_text(self) -> str:
        return self._log_text

    @Property(bool, notify=is_connected_changed)
    def is_connected(self) -> bool:
        return self._is_connected

    @Property(str, notify=command_text_changed)
    def command_text(self) -> str:
        return self._command_text

    @command_text.setter
    def command_text(self, value: str):
        if self._command_text != value:
            self._command_text = value
            self.command_text_changed.emit()

    @Property(QObject, constant=True)
    def port_list_model(self) -> QStringListModel:
        return self._port_list_model

    @Property(str, notify=platform_name_changed)
    def platform_name(self) -> str:
        return self._platform_name

    @Property(dict, notify=system_info_changed)
    def system_info(self) -> dict:
        return self._system_info

    @Property(list, notify=system_info_keys_changed)
    def system_info_keys(self) -> list:
        if self._system_info_service and hasattr(self._system_info_service, 'commands'):
            return list(self._system_info_service.commands.keys())
        return []

    @Slot()
    def refresh_ports(self):
        """Refreshes the list of available serial ports."""
        ports = self._model.get_available_ports()
        if not ports:
            self._append_log("No serial ports found.")
            port_strings = []
        else:
            port_strings = [f"{p.device} - {p.description}" for p in sorted(ports, key=lambda p: p.device)]
        
        self._port_list_model.setStringList(port_strings)

    @Slot(str, str)
    def toggle_connection(self, port_text: str, baud_rate_text: str):
        """Connects or disconnects the device based on the current state."""
        if self._is_connected:
            self._model.disconnect_device()
        else:
            if not port_text:
                self._append_log("Please select a port.")
                return
            if not baud_rate_text:
                self._append_log("Please select a baud rate.")
                return

            try:
                baud_rate = int(baud_rate_text)
                # Extract device path from "COM3 - Description"
                port_device = port_text.split(' ')[0]
                self._append_log(f"Attempting to connect to {port_device} at {baud_rate} baud...")
                self._model.connect_device(port=port_device, baudrate=baud_rate)
            except ValueError:
                self._append_log(f"Invalid baud rate: {baud_rate_text}")

    @Slot()
    def open_system_info_view(self):
        """Opens the system info view and starts data collection."""
        self.open_system_info_requested.emit()
        self._system_info_service.collect_system_info()

    @Slot()
    def send_command(self):
        """Sends the command from the command_text property."""
        if self._command_text:
            self._append_log(f"[SEND]: {self._command_text}")
            self._model.send_command_queued(self._command_text)
            self.command_text = "" # Clear input after sending

    @Slot(bytes)
    def send_interrupt_bytes(self, interrupt_bytes: bytes):
        """Sends an interrupt byte sequence from the view."""
        if self._is_connected:
            # For logging purposes, map bytes to a friendly name
            log_message = f"[SEND]: Interrupt ({interrupt_bytes.hex()})"
            if interrupt_bytes == b'\x03':
                log_message = "[SEND]: Ctrl+C (Interrupt)"
            elif interrupt_bytes == b'\x04':
                log_message = "[SEND]: Ctrl+D (EOF)"
            elif interrupt_bytes == b'\x1b':
                log_message = "[SEND]: ESC"
            
            self._append_log(log_message)
            self._model.send_command_queued(interrupt_bytes)

    @Slot()
    def clean_up(self):
        """Should be called before application quits to ensure clean disconnection."""
        self._model.disconnect_device()

    # =================================================================================
    # Private slots to handle signals from the Model and Services
    # =================================================================================
    @Slot(bool, str)
    def on_connection_result(self, success: bool, message: str):
        self._append_log(message)
        if success != self._is_connected:
            self._is_connected = success
            self.is_connected_changed.emit()
        
        if success:
            self._detection_service.start_detection()
        else:
            self.on_platform_detected("Unknown")

    @Slot(bool, str)
    def on_disconnection_result(self, success: bool, message: str):
        self._append_log(message)
        # Stop detection service regardless of disconnection success
        self._detection_service.stop_detection()
        self._system_info_service.stop_collection()
        
        # Only update state if disconnection was successful or wasn't already disconnected
        if success and self._is_connected:
            self._is_connected = False
            self.is_connected_changed.emit()
            self._system_info.clear()
            self.system_info_reset.emit()
        
        # Reset platform name on disconnect
        self.on_platform_detected("Unknown")

    @Slot(str)
    def on_data_received(self, data: str):
        self._append_log(data)

    @Slot(str)
    def on_platform_detected(self, platform_name: str):
        if self._platform_name != platform_name:
            self._platform_name = platform_name
            self.platform_name_changed.emit()
        
            if self.platform_name == "Unknown":
                return  
            # Initialize system info service with the detected platform name
            self._system_info_service = SystemInfoService(device_model=self._model, platform_name=self._platform_name)
            self._system_info_service.info_updated.connect(self.on_info_updated)
            self.system_info_keys_changed.emit()
    
    @Slot(bool, str)
    def on_info_updated(self, key: str, result: str):
        self._system_info[key] = result
        self.system_info_changed.emit(key, result)

    # =================================================================================
    # Helper methods
    # =================================================================================
    def _append_log(self, message: str):
        """Appends a message to the log and emits change signal."""
        self._log_text += message + "\n"
        # logger.debug(message)
        self.log_text_changed.emit()
