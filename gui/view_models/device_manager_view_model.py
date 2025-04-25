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
        
        # Initialize SystemInfoService
        from core.services.system_info import SystemInfoService
        self.system_info_service = SystemInfoService(self._serial_worker)
        
    def cleanup(self):
        """Release resources and clean up"""
        # Prevent duplicate cleanup
        if hasattr(self, '_is_cleaning_up') and self._is_cleaning_up:
            logger.warning("DeviceManagerViewModel is already in the cleanup process, avoid duplicate cleanup")
            return
            
        # Security check: If the C++ object has been deleted, skip cleanup
        try:
            # Try a simple operation to check if the object is valid
            self.blockSignals(True)
        except RuntimeError as e:
            if "C++ object" in str(e) and "deleted" in str(e):
                logger.warning("DeviceManagerViewModel C++ object has been deleted, skip cleanup")
                return
            # If it's another RuntimeError, continue trying to clean up
        except Exception as e:
            logger.warning(f"Error checking object validity: {e}")
        
        # Set cleanup flag
        self._is_cleaning_up = True
        
        logger.info("DeviceManagerViewModel starts cleaning up resources")
        
        try:
            # 1. Ensure any active timers are stopped
            if hasattr(self, '_refresh_timer') and self._refresh_timer and self._refresh_timer.isActive():
                self._refresh_timer.stop()
                logger.debug("Stopped device refresh timer")
            
            # 2. Disconnect all signal connections - Disconnect signals before disconnecting devices to avoid triggering callbacks
            try:
                # First block sending new signals
                self.blockSignals(True)
                
                # Then disconnect signals from worker
                if hasattr(self, '_serial_worker') and self._serial_worker:
                    try:
                        # Check if signals have receivers
                        try:
                            self._serial_worker.connection_result.disconnect(self._on_connection_completed)
                        except Exception:
                            pass
                            
                        try:
                            self._serial_worker.disconnection_result.disconnect(self._on_disconnection_completed)
                        except Exception:
                            pass
                            
                        try:
                            self._serial_worker.command_result.disconnect(self._on_command_completed)
                        except Exception:
                            pass
                            
                        logger.debug("Worker signal connections disconnected")
                    except Exception as e:
                        logger.warning(f"Error disconnecting worker signals: {e}")
            except Exception as e:
                logger.warning(f"Error disconnecting signal connections: {e}")
            
            # 3. Disconnect all connected devices - Since signals have been disconnected, this will not trigger callbacks
            if hasattr(self, 'device_manager') and self.device_manager:
                try:
                    # Directly use the disconnect_all method of device_manager, not through this class
                    logger.info("Disconnect all devices directly")
                    self.device_manager.disconnect_all()
                except Exception as e:
                    logger.error(f"Error disconnecting all devices: {e}")
            
            # 4. Stop and release worker thread
            if hasattr(self, '_serial_worker') and self._serial_worker:
                try:
                    logger.info("Stopping and releasing worker thread")
                    # Ensure the thread object exists and is accessible
                    if hasattr(self._serial_worker, 'thread') and self._serial_worker.thread:
                        # Check if the thread is still running
                        if self._serial_worker.thread.isRunning():
                            # Try to exit the worker thread normally
                            self._serial_worker.thread.requestInterruption()
                            if not self._serial_worker.thread.wait(1000):
                                logger.warning("Worker thread unresponsive, force termination")
                                self._serial_worker.thread.terminate()
                                self._serial_worker.thread.wait(1000)  # Give the thread more time to terminate
                            logger.debug("Device worker thread stopped")
                        
                    # Call the cleanup method of serial_worker (if it exists)
                    if hasattr(self._serial_worker, 'cleanup'):
                        try:
                            self._serial_worker.cleanup()
                        except Exception as e:
                            logger.warning(f"Error calling serial_worker.cleanup(): {e}")
                        
                    # Clear the reference and notify Python to reclaim memory
                    worker_ref = self._serial_worker
                    self._serial_worker = None
                    del worker_ref
                    
                except Exception as e:
                    logger.error(f"Error stopping worker thread: {e}")
            
            # 5. Release device manager model
            if hasattr(self, 'device_manager') and self.device_manager:
                try:
                    logger.info("Cleaning up device manager model")
                    device_manager_ref = self.device_manager
                    self.device_manager = None
                    del device_manager_ref
                    logger.debug("Device manager model cleaned up")
                except Exception as e:
                    logger.error(f"Error cleaning up device manager model: {e}")
            
            # 6. Clear all device-related collections
            if hasattr(self, 'connected_devices'):
                self.connected_devices.clear()
            
        except Exception as e:
            logger.error(f"Error cleaning up DeviceManagerViewModel resources: {e}")
        finally:
            # Regardless of success or failure, reset the cleanup flag and record completion
            self._is_cleaning_up = False
            logger.info("DeviceManagerViewModel resources cleaned up")
        
    def __del__(self):
        """Ensure resources are released"""
        try:
            # Check if the object is still valid
            if hasattr(self, 'blockSignals'):
                try:
                    # Try a simple operation to test object validity
                    self.blockSignals(True)
                    # If the object is valid and not in the cleanup process, call cleanup
                    if not hasattr(self, '_is_cleaning_up') or not self._is_cleaning_up:
                        logger.debug("DeviceManagerViewModel destructor calling cleanup")
                        self.cleanup()
                except Exception:
                    # Object is invalid, ignore cleanup
                    pass
        except Exception:
            # Avoid throwing exceptions in the destructor
            pass
        
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
