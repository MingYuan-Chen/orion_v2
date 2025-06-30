from PySide6.QtCore import QObject, Signal, Slot, QMutex, QThread
from typing import Dict, Optional, List, Any
import uuid
import time
from core.models.device_manager_model import DeviceManagerModel
from core.services.reboot_handler import RebootHandler
from util.logger import logger
import sys

class SerialDeviceWorker(QObject):
    """
    Serial Device Worker Class
    
    Responsible for executing device operations in a separate thread, such as connecting, disconnecting, and sending commands.
    Each operation completes by emitting a signal to notify the result.
    Supports concurrent multi-device operations, and can be extended for various device services.
    """
    # Define external signals
    connection_result = Signal(str, bool, str)  # device_id, success, message
    disconnection_result = Signal(str, bool, str)  # device_id, success, message
    command_result = Signal(str, str, str)  # device_id, command, response
    
    # Define internal signals for passing commands between threads
    _connect_device_signal = Signal(str, str, int, int)  # device_id, port, baudrate, timeout
    _disconnect_device_signal = Signal(str)  # device_id
    _send_command_signal = Signal(str, str, int)  # device_id, command, timeout
    
    def __init__(self, device_manager: DeviceManagerModel):
        super().__init__()
        self.device_manager = device_manager
        # Reserve a mutex for command execution (currently not used due to signal-based design can handle concurrency)
        self.command_mutex = QMutex()
        
        # Add a flag to prevent re-entry
        self._is_cleaning = False
        
        # Create RebootHandler for special reboot command processing
        self.reboot_handler = RebootHandler(device_manager)
        self.reboot_handler.reboot_completed.connect(self._on_reboot_completed)
        self.reboot_handler.reboot_failed.connect(self._on_reboot_failed)
        
        # Create thread and move worker to thread
        self.thread = QThread()
        self.thread.setObjectName(f"SerialDeviceWorker_{uuid.uuid4().hex[:8]}")
        self.moveToThread(self.thread)
        
        # Connect thread signals
        self.thread.started.connect(self._on_thread_started)
        self.thread.finished.connect(self._on_thread_finished)
        
        # Connect internal signals to actual execution slots
        self._connect_device_signal.connect(self._execute_connect_device)
        self._disconnect_device_signal.connect(self._execute_disconnect_device)
        self._send_command_signal.connect(self._execute_send_command)
        
        # Start thread
        self.thread.start()
        
    def _on_thread_started(self):
        """Handle thread start"""
        logger.info(f"SerialDeviceWorker thread started: {self.thread.objectName()}")
        
    def _on_thread_finished(self):
        """Handle thread finish"""
        logger.info(f"SerialDeviceWorker thread finished: {self.thread.objectName()}")
        
    def cleanup(self):
        """Clean up resources, stop thread"""
        # Prevent duplicate cleanup
        if hasattr(self, '_is_cleaning') and self._is_cleaning:
            logger.warning("SerialDeviceWorker is already in the cleanup process, avoid duplicate calls")
            return
            
        # Set cleanup flag
        self._is_cleaning = True
            
        logger.info("SerialDeviceWorker starts cleaning up resources")
        
        try:
            # Clean up RebootHandler first
            if hasattr(self, 'reboot_handler'):
                logger.debug("Cleaning up RebootHandler")
                self.reboot_handler.cleanup()
                self.reboot_handler = None
            # First disconnect all signal connections
            try:
                # Block sending new signals
                self.blockSignals(True)
                
                # Disconnect signal connections safely - PySide6's Signal does not have a receivers() method
                # Try to disconnect specific connections directly, using try-except to handle possible errors
                
                # Try to disconnect internal signal connections
                try:
                    self._connect_device_signal.disconnect(self._execute_connect_device)
                    logger.debug("Disconnected _connect_device_signal signal")
                except (TypeError, RuntimeError):
                    # Signal may not be connected or already disconnected
                    pass
                except Exception as e:
                    logger.warning(f"Error disconnecting _connect_device_signal: {e}")
                
                try:
                    self._disconnect_device_signal.disconnect(self._execute_disconnect_device)
                    logger.debug("Disconnected _disconnect_device_signal signal")
                except (TypeError, RuntimeError):
                    # Signal may not be connected or already disconnected
                    pass
                except Exception as e:
                    logger.warning(f"Error disconnecting _disconnect_device_signal: {e}")
                
                try:
                    self._send_command_signal.disconnect(self._execute_send_command)
                    logger.debug("Disconnected _send_command_signal signal")
                except (TypeError, RuntimeError):
                    # Signal may not be connected or already disconnected
                    pass
                except Exception as e:
                    logger.warning(f"Error disconnecting _send_command_signal: {e}")
                
                # Do not try to disconnect external signals, because we do not know who connected them
                # Just keep blockSignals(True)
                
                logger.debug("SerialDeviceWorker signal processing completed")
            except Exception as e:
                logger.warning(f"Error disconnecting signals: {e}")
            
            # Then stop the thread - Note: Keep a reference to the thread first
            thread_ref = None
            if hasattr(self, 'thread') and self.thread:
                thread_ref = self.thread  # Save reference
                
                if thread_ref.isRunning():
                    logger.debug(f"Stopping thread: {thread_ref.objectName()}")
                    # Disconnect the thread's signals first
                    try:
                        thread_ref.started.disconnect()
                    except Exception:
                        pass  # Ignore errors
                        
                    try:
                        thread_ref.finished.disconnect()
                    except Exception:
                        pass  # Ignore errors
                        
                    # Now try to stop the thread
                    thread_ref.quit()
                    if not thread_ref.wait(2000):  # Wait up to 2 seconds
                        logger.warning(f"Thread unresponsive, force termination: {thread_ref.objectName()}")
                        thread_ref.terminate()
                        thread_ref.wait(1000)  # Wait another second to ensure termination
                    logger.debug(f"Thread stopped: {thread_ref.objectName()}")
                
                # Clear object references, but keep local references for completion
                self.thread = None
                
            # Finally ensure the thread is completely cleaned up
            if thread_ref:
                try:
                    # Ensure thread memory is released
                    thread_ref.deleteLater()
                except Exception as e:
                    logger.warning(f"Error deleting thread object: {e}")
                    
            # Clear all other references
            self.device_manager = None
            
        except Exception as e:
            logger.error(f"Error cleaning up SerialDeviceWorker resources: {e}")
        finally:
            # Regardless of success or failure, reset the cleanup flag
            self._is_cleaning = False
            logger.info("SerialDeviceWorker resources cleaned up")
                
    def __del__(self):
        """Destructor, ensure resources are released"""
        try:
            logger.debug("SerialDeviceWorker is being destroyed")
            # Avoid calling cleanup in the destructor, which may cause problems
        except Exception:
            # Avoid throwing exceptions in the destructor
            pass
    
    # External interface methods - these methods are called from the main thread, only emit signals
        
    def connect_device(self, device_id: str, port: str, baudrate: int, timeout: int):
        """Connect serial device - execute in worker thread by emitting signals
        
        Args:
            device_id: device ID
            port: serial port name
            baudrate: baud rate
            timeout: timeout (seconds)
        """
        logger.info(f"Request to connect device {device_id} to port {port}")
        self._connect_device_signal.emit(device_id, port, baudrate, timeout)
            
    def disconnect_device(self, device_id: str):
        """Disconnect device - execute in worker thread by emitting signals
        
        Args:
            device_id: device ID
        """
        logger.info(f"Request to disconnect device {device_id}")
        self._disconnect_device_signal.emit(device_id)
            
    def send_command(self, device_id: str, command: str, timeout: int):
        """Send command to device - execute in worker thread by emitting signals
        
        Args:
            device_id: device ID
            command: command to send
            timeout: timeout (seconds)
        """
        logger.info(f"Request to send command to device {device_id}: {command}")
        self._send_command_signal.emit(device_id, command, timeout)
    
    # Actual execution methods - these slots are executed in the worker thread
    
    @Slot(str, str, int, int)
    def _execute_connect_device(self, device_id: str, port: str, baudrate: int, timeout: int):
        """Actual execute device connection operation (in worker thread)"""
        try:
            logger.info(f"Connecting device {device_id} to port {port}")
            
            # Create device and connect
            device = self.device_manager.create_serial_device(device_id, port, baudrate, timeout)
            if not device:
                self.connection_result.emit(device_id, False, f"Failed to create device {device_id}")
                return
                
            success = device.connect()
            if success:
                self.connection_result.emit(device_id, True, f"Successfully connected device {device_id} to port {port}")
            else:
                self.connection_result.emit(device_id, False, f"Failed to connect device {device_id} to port {port}")
        except Exception as e:
            logger.error(f"Error connecting device {device_id}: {str(e)}")
            self.connection_result.emit(device_id, False, f"Error connecting device: {str(e)}")
    
    @Slot(str)        
    def _execute_disconnect_device(self, device_id: str):
        """Actual execute device disconnection operation (in worker thread)"""
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
        """Actual execute send command operation (in worker thread)"""
        try:
            # Check if this is a reboot command
            if command.strip().lower() == "reboot":
                logger.info(f"Detected reboot command for device {device_id}, using RebootHandler")
                self.reboot_handler.handle_reboot(device_id, timeout)
                return
            
            # Check if device is currently rebooting
            if self.reboot_handler.is_device_rebooting(device_id):
                logger.warning(f"Device {device_id} is rebooting, command ignored: {command}")
                self.command_result.emit(device_id, command, "Error: Device is rebooting")
                return
            
            # use clear format to log command, ensure it is visible in system log
            logger.info(f"COMMAND: [{device_id}] >>> {command}")
            
            # Execute command
            response = self.device_manager.send_command(device_id, command, timeout)
            
            # use clear format to log response, ensure it is visible in system log
            logger.info(f"RESPONSE: [{device_id}] <<< {response}")
            
            self.command_result.emit(device_id, command, response)
        except Exception as e:
            logger.error(f"Error sending command {command} to device {device_id}: {str(e)}")
            self.command_result.emit(device_id, command, f"Error: {str(e)}")
    
    # RebootHandler signal handlers
    
    @Slot(str, str, str)
    def _on_reboot_completed(self, device_id: str, command: str, response: str):
        """Handle reboot completion signal from RebootHandler"""
        logger.info(f"Reboot completed for device {device_id}: {response}")
        # Forward the signal to upper layers
        self.command_result.emit(device_id, command, response)
    
    @Slot(str, str, str)
    def _on_reboot_failed(self, device_id: str, command: str, error_message: str):
        """Handle reboot failure signal from RebootHandler"""
        logger.error(f"Reboot failed for device {device_id}: {error_message}")
        # Forward the signal to upper layers
        self.command_result.emit(device_id, command, f"Error: {error_message}")
    
    # Public methods for RebootHandler management
    
    def is_device_rebooting(self, device_id: str) -> bool:
        """Check if device is currently rebooting"""
        return self.reboot_handler.is_device_rebooting(device_id)
    
    def cancel_reboot(self, device_id: str):
        """Cancel device reboot"""
        self.reboot_handler.cancel_reboot(device_id)
    
    def get_rebooting_devices(self) -> Dict[str, Dict]:
        """Get list of devices currently rebooting"""
        return self.reboot_handler.get_rebooting_devices()
    
    def set_reboot_login_check_command(self, command: str):
        """
        Set reboot login check command
        
        Args:
            command: Check command, e.g.:
                    "root" - Default command (if device supports)
                    "echo ready" - More general, always successful
                    "whoami" - Check current user
                    "pwd" - Check current directory
        """
        self.reboot_handler.set_login_check_command(command)


if __name__ == "__main__":
    
    def main():
        from core.models.device_manager_model import DeviceManagerModel
        from util.logger import logger
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer

        # Create application
        app = QApplication(sys.argv)    
        device_manager = DeviceManagerModel()
        serial_device_worker = SerialDeviceWorker(device_manager)

        def on_connection_result(device_id, success, message):
            logger.info(f"Connection result: {device_id}, {success}, {message}")
            serial_device_worker.send_command("device1", "ls", 5)

        def on_disconnection_result(device_id, success, message):
            logger.info(f"Disconnection result: {device_id}, {success}, {message}")

        def on_command_result(device_id, command, response):
            logger.info(f"Command result: {device_id}, {command}, {response}")
            serial_device_worker.disconnect_device("device1")
        # Connect signals
        serial_device_worker.connection_result.connect(on_connection_result)
        serial_device_worker.disconnection_result.connect(on_disconnection_result)
        serial_device_worker.command_result.connect(on_command_result)

        # Test connection
        serial_device_worker.connect_device("device1", "COM4", 115200, 10)
        
        
        QTimer.singleShot(25000, lambda: serial_device_worker.cleanup())
        QTimer.singleShot(30000, lambda: QApplication.quit())
        sys.exit(app.exec())

    sys.exit(main())


