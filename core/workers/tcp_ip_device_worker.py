from PySide6.QtCore import QObject, Signal, Slot, QMutex, QThread
from typing import Dict, Optional, List, Any
import uuid
import time
from core.models.device_manager_model import DeviceManagerModel
from core.services.reboot_handler import RebootHandler
from util.logger import logger
import sys

class TcpIpDeviceWorker(QObject):
    """
    TCP/IP Device Worker Class
    
    Responsible for executing device operations in a separate thread, such as connecting, disconnecting, and sending commands over TCP/IP.
    """
    # Define external signals
    connection_result = Signal(str, bool, str)  # device_id, success, message
    disconnection_result = Signal(str, bool, str)  # device_id, success, message
    command_result = Signal(str, str, str)  # device_id, command, response
    
    # Define internal signals for passing commands between threads
    _connect_device_signal = Signal(str, str, int, int)  # device_id, host, port, timeout
    _disconnect_device_signal = Signal(str)  # device_id
    _send_command_signal = Signal(str, str, int)  # device_id, command, timeout
    _send_control_sequence_signal = Signal(str, str)  # device_id, control_char
    
    def __init__(self, device_manager: DeviceManagerModel):
        super().__init__()
        self.device_manager = device_manager
        self.command_mutex = QMutex()
        self._is_cleaning = False
        
        # RebootHandler might need adjustment if it has serial-specific logic
        # For now, we assume it can work with the device_manager abstractly
        self.reboot_handler = RebootHandler(device_manager)
        self.reboot_handler.reboot_completed.connect(self._on_reboot_completed)
        self.reboot_handler.reboot_failed.connect(self._on_reboot_failed)
        
        self.thread = QThread()
        self.thread.setObjectName(f"TcpIpDeviceWorker_{uuid.uuid4().hex[:8]}")
        self.moveToThread(self.thread)
        
        self.thread.started.connect(self._on_thread_started)
        self.thread.finished.connect(self._on_thread_finished)
        
        self._connect_device_signal.connect(self._execute_connect_device)
        self._disconnect_device_signal.connect(self._execute_disconnect_device)
        self._send_command_signal.connect(self._execute_send_command)
        self._send_control_sequence_signal.connect(self._execute_send_control_sequence)
        
        self.thread.start()
        
    def _on_thread_started(self):
        logger.info(f"TcpIpDeviceWorker thread started: {self.thread.objectName()}")
        
    def _on_thread_finished(self):
        logger.info(f"TcpIpDeviceWorker thread finished: {self.thread.objectName()}")

    def cleanup(self):
        if self._is_cleaning:
            return
        self._is_cleaning = True
        logger.info("TcpIpDeviceWorker starts cleaning up resources")
        if self.thread.isRunning():
            self.thread.quit()
            if not self.thread.wait(2000):
                self.thread.terminate()
                self.thread.wait(1000)
        self._is_cleaning = False

    # External interface methods
        
    def connect_device(self, device_id: str, host: str, port: int, timeout: int):
        logger.info(f"Request to connect device {device_id} to {host}:{port}")
        self._connect_device_signal.emit(device_id, host, port, timeout)
            
    def disconnect_device(self, device_id: str):
        logger.info(f"Request to disconnect device {device_id}")
        self._disconnect_device_signal.emit(device_id)
            
    def send_command(self, device_id: str, command: str, timeout: int):
        logger.info(f"Request to send command to device {device_id}: {command}")
        self._send_command_signal.emit(device_id, command, timeout)
    
    def send_control_sequence(self, device_id: str, control_char: str):
        logger.info(f"Request to send control sequence '{control_char}' to device {device_id}")
        self._send_control_sequence_signal.emit(device_id, control_char)
    
    # Actual execution methods (slots)
    
    @Slot(str, str, int, int)
    def _execute_connect_device(self, device_id: str, host: str, port: int, timeout: int):
        try:
            logger.info(f"Connecting device {device_id} to {host}:{port}")
            device = self.device_manager.create_tcp_ip_device(device_id, host, port, timeout)
            if not device:
                self.connection_result.emit(device_id, False, f"Failed to create device {device_id}")
                return
                
            success = device.connect()
            if success:
                self.connection_result.emit(device_id, True, f"Successfully connected device {device_id} to {host}:{port}")
            else:
                self.connection_result.emit(device_id, False, f"Failed to connect device {device_id} to {host}:{port}")
        except Exception as e:
            logger.error(f"Error connecting device {device_id}: {str(e)}")
            self.connection_result.emit(device_id, False, f"Error connecting device: {str(e)}")
    
    @Slot(str)        
    def _execute_disconnect_device(self, device_id: str):
        try:
            logger.info(f"Disconnecting device {device_id}")
            success = self.device_manager.disconnect_device(device_id)
            if success:
                self.disconnection_result.emit(device_id, True, f"Successfully disconnected device {device_id}")
            else:
                self.disconnection_result.emit(device_id, False, f"Failed to disconnect device {device_id}")
        except Exception as e:
            logger.error(f"Error disconnecting device {device_id}: {str(e)}")
            self.disconnection_result.emit(device_id, False, f"Error disconnecting device: {str(e)}")
    
    @Slot(str, str, int)        
    def _execute_send_command(self, device_id: str, command: str, timeout: int):
        try:
            if command.strip().lower() == "reboot":
                self.reboot_handler.handle_reboot(device_id, timeout)
                return
            
            if self.reboot_handler.is_device_rebooting(device_id):
                self.command_result.emit(device_id, command, "Error: Device is rebooting")
                return
            
            logger.info(f"COMMAND: [{device_id}] >>> {command}")
            response = self.device_manager.send_command(device_id, command, timeout)
            logger.info(f"RESPONSE: [{device_id}] <<< {response}")
            self.command_result.emit(device_id, command, response)
        except Exception as e:
            logger.error(f"Error sending command {command} to device {device_id}: {str(e)}")
            self.command_result.emit(device_id, command, f"Error: {str(e)}")
    
    @Slot(str, str)
    def _execute_send_control_sequence(self, device_id: str, control_char: str):
        try:
            logger.info(f"CONTROL: [{device_id}] >>> Sending '{control_char}' sequence")
            device = self.device_manager.get_device(device_id)
            if not device:
                self.command_result.emit(device_id, f"CONTROL:{control_char}", "Error: Device not found")
                return
            
            # Assumes the device model has a `send_control_sequence` method
            success = device.send_control_sequence(control_char)
            if success:
                self.command_result.emit(device_id, f"CONTROL:{control_char}", f"Control sequence '{control_char}' sent")
            else:
                self.command_result.emit(device_id, f"CONTROL:{control_char}", f"Error: Failed to send '{control_char}' sequence")
        except Exception as e:
            logger.error(f"Error sending '{control_char}' to device {device_id}: {str(e)}")
            self.command_result.emit(device_id, f"CONTROL:{control_char}", f"Error: {str(e)}")
    
    # RebootHandler signal handlers
    @Slot(str, str, str)
    def _on_reboot_completed(self, device_id: str, command: str, response: str):
        self.command_result.emit(device_id, command, response)
    
    @Slot(str, str, str)
    def _on_reboot_failed(self, device_id: str, command: str, error_message: str):
        self.command_result.emit(device_id, command, f"Error: {error_message}")

    def is_device_rebooting(self, device_id: str) -> bool:
        return self.reboot_handler.is_device_rebooting(device_id)
