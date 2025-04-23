from PySide6.QtCore import QObject, Signal, Slot
from typing import Dict, List, Optional, Any
import time
from core.models.device_manager_model import DeviceManagerModel
from core.workers.serial_device_worker import SerialDeviceWorker
from util.logger import logger


class DeviceManagerViewModel(QObject):
    """
    Device Manager View Model
    
    Manage device connection, disconnection and command sending operations.
    Provide signals to notify the UI layer of operation results.
    """
    # Connection/disconnection signals
    connection_result = Signal(str, bool, str)  # device_id, success, message
    disconnection_result = Signal(str, bool, str)  # device_id, success, message
    device_list_changed = Signal(list)  # devices_list
    
    # Command execution signals
    command_result = Signal(str, str, str)  # device_id, command, response
    
    def __init__(self, device_manager: DeviceManagerModel = None):
        super().__init__()
        # Initialize device manager
        self.device_manager = device_manager or DeviceManagerModel()
        self.connected_devices = {}  # device_id: device_info
        
        # Create device worker thread
        self._serial_worker = SerialDeviceWorker(self.device_manager)
        
        # Connection signals
        self._serial_worker.connection_result.connect(self._on_connection_completed)
        self._serial_worker.disconnection_result.connect(self._on_disconnection_completed)
        self._serial_worker.command_result.connect(self._on_command_completed)
        
        # 初始化 SystemInfoService
        from core.services.system_info import SystemInfoService
        self.system_info_service = SystemInfoService(self._serial_worker)
        
    def cleanup(self):
        """Clean up all resources"""
        # Disconnect all devices
        for device_id in list(self.connected_devices.keys()):
            self.disconnect_device(device_id)
            
        # Clean up worker thread
        if self._serial_worker:
            self._serial_worker.cleanup()
            
    def __del__(self):
        """Ensure resources are released"""
        self.cleanup()
        
    @Slot(str, bool, str)
    def _on_connection_completed(self, device_id: str, success: bool, message: str):
        """Handle connection operation completion"""
        if success:
            # Parse device ID information to create device info object
            parts = device_id.split('_')
            device_type = parts[0] if len(parts) > 0 else "serial"
            address = parts[1] if len(parts) > 1 else device_id
            
            # Create device info
            device_info = {
                'id': device_id,
                'name': f"{device_type.capitalize()} Device ({address})",
                'type': device_type.capitalize(),
                'address': address,
                'status': 'Connected',
                'details': {}  # Specific details can be added according to device type in other places
            }
            
            # Store device info
            self.connected_devices[device_id] = device_info
                
            # Emit signal
            self.connection_result.emit(device_id, success, message)
            self.device_list_changed.emit(list(self.connected_devices.values()))
        
    @Slot(str, bool, str)
    def _on_disconnection_completed(self, device_id: str, success: bool, message: str):
        """Handle disconnection operation completion"""
        if success and device_id in self.connected_devices:
            del self.connected_devices[device_id]
            
        # Emit signal
        self.disconnection_result.emit(device_id, success, message)
        self.device_list_changed.emit(list(self.connected_devices.values()))
        
    @Slot(str, str, str)
    def _on_command_completed(self, device_id: str, command: str, response: str):
        """Handle command execution completion"""
        self.command_result.emit(device_id, command, response)
        
    def connect_serial_device(self, device_id: str, port: str, baudrate: int = 115200, timeout: int = 3):
        """Connect serial device"""
        logger.info(f"Request to connect device {device_id} to port {port}")
        
        if device_id in self.connected_devices:
            self.connection_result.emit(device_id, False, f"Device {device_id} is already connected")
            return
        
        # Use worker thread to connect device
        self._serial_worker.connect_device(device_id, port, baudrate, timeout)
        
    def disconnect_device(self, device_id: str):
        """Disconnect device"""
        logger.info(f"Request to disconnect device {device_id}")
        
        if device_id not in self.connected_devices:
            self.disconnection_result.emit(device_id, False, f"Device {device_id} is not connected")
            return
            
        # Use worker thread to disconnect device
        self._serial_worker.disconnect_device(device_id)
        
    def send_command(self, device_id: str, command: str, timeout: int = 5):
        """Send command to device"""
        logger.info(f"Request to send command to device {device_id}: {command}")
        
        if device_id not in self.connected_devices:
            self.command_result.emit(device_id, command, f"Error: Device {device_id} is not connected")
            return
            
        # Use worker thread to send command
        self._serial_worker.send_command(device_id, command, timeout)
        
    def get_connected_devices(self) -> List[Dict[str, Any]]:
        """Get list of connected devices"""
        return list(self.connected_devices.values())
        
    def disconnect_all_devices(self):
        """Disconnect all devices"""
        logger.info("Request to disconnect all devices")
        
        for device_id in list(self.connected_devices.keys()):
            self.disconnect_device(device_id)

    def update_device_info(self, device_id: str, details: Dict[str, Any]):
        """Update device details
        
        Args:
            device_id: device ID
            details: details dictionary
        """
        if device_id in self.connected_devices:
            # Update details
            self.connected_devices[device_id]['details'].update(details)
            # Notify device list has changed
            self.device_list_changed.emit(list(self.connected_devices.values()))
